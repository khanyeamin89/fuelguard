import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import qrcode
import io
import re

# --- ১. কনফিগারেশন ও কানেকশন ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Secrets missing! Please add SUPABASE_URL and SUPABASE_KEY.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app" 

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    return f"{base_pin}{datetime.now().strftime('%d')}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. আইডি ফরম্যাটিং ফাংশন ---
def format_id_for_search(user_input):
    if not user_input: return ""
    return re.sub(r'[-\s]', '', str(user_input)).upper()

# --- ৩. ডাটাবেজ ফাংশনসমূহ ---
def get_rider_by_id(search_id):
    clean_target = format_id_for_search(search_id)
    try:
        # প্রথমে সরাসরি চেক
        res = supabase.table("riders").select("*").eq("rider_id", search_id.upper().strip()).execute()
        if res.data: return res.data[0]
        
        # ড্যাশ ছাড়া চেক (Fallback)
        all_riders = supabase.table("riders").select("*").execute()
        for r in all_riders.data:
            if format_id_for_search(r['rider_id']) == clean_target:
                return r
        return None
    except: return None

def register_user(data):
    try:
        supabase.table("riders").insert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

def update_refill(rider_id, liters, fuel_type, photo_file=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if photo_file:
        file_name = f"{rider_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        supabase.storage.from_("fuel_photos").upload(file_name, photo_file.getvalue())
    
    supabase.table("riders").update({
        "last_refill": now,
        "liters": float(liters),
        "fuel_type": fuel_type
    }).eq("rider_id", rider_id).execute()

# --- ৪. রোল সিলেকশন ---
if "user_role" not in st.session_state:
    st.session_state.user_role = None

if st.session_state.user_role is None:
    st.title("⛽ FuelGuard Pro")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏍️ User Portal (Register/Status)", use_container_width=True):
            st.session_state.user_role = "User"; st.rerun()
    with col2:
        if st.button("🏢 Pump Station (PIN Required)", use_container_width=True):
            st.session_state.user_role = "Pump"; st.rerun()
    st.stop()

# --- ৫. ইউজার ইন্টারফেস (Rider, Farmer, Govt) ---
if st.session_state.user_role == "User":
    if st.sidebar.button("⬅️ Home"):
        st.session_state.user_role = None; st.rerun()
    
    st.title("👤 User Portal")
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস ও হিস্ট্রি", "📝 নতুন নিবন্ধন"])
    
    with tab1:
        search_id = st.text_input("আইডি বা রেজিস্ট্রেশন নাম্বার লিখুন")
        if search_id:
            user = get_rider_by_id(search_id)
            if user:
                st.success(f"স্বাগতম, **{user['name']}** [{user.get('category', 'Rider')}]")
                
                # হিস্ট্রি কার্ড
                c1, c2, c3 = st.columns(3)
                c1.metric("সর্বশেষ রিফিল", f"{user['liters']} L")
                c2.metric("জ্বালানির ধরন", user.get('fuel_type', 'N/A'))
                c3.metric("ক্যাটাগরি", user.get('category', 'General'))
                
                # এলিজিবিলিটি লজিক
                is_exempt = user.get('category') in ['Farmer', 'Govt Emergency']
                if is_exempt:
                    st.info("✅ আপনি জরুরি ক্যাটাগরিতে আছেন। আপনার জন্য ৭২ ঘণ্টার লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লকড! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
            else: st.warning("আইডি পাওয়া যায়নি।")

    with tab2:
        category = st.selectbox("নিবন্ধনের ধরন নির্বাচন করুন", ["Rider (General)", "Farmer (কৃষক)", "Govt Emergency (সরকারি জরুরি সেবা)"])
        
        with st.form("registration_form"):
            user_data = {"category": category, "liters": 0, "last_refill": None}
            
            if category == "Rider (General)":
                user_data["rider_id"] = st.text_input("যানবাহন রেজিস্ট্রেশন নং (যেমন: DHAKA-METRO-12-3456)").upper()
                user_data["name"] = st.text_input("নাম")
            
            elif category == "Farmer (কৃষক)":
                user_data["name"] = st.text_input("কৃষকের নাম")
                user_data["address"] = st.text_input("ঠিকানা")
                user_data["rider_id"] = st.text_input("NID নাম্বার (এটিই আপনার আইডি হবে)")
                user_data["uno_cert"] = st.text_input("UNO ইস্যু করা সার্টিফিকেট নং")
            
            elif category == "Govt Emergency (সরকারি জরুরি সেবা)":
                user_data["name"] = st.text_input("চালকের নাম")
                user_data["workplace"] = st.text_input("কর্মস্থল/দপ্তর")
                user_data["work_id"] = st.text_input("Work ID নং")
                user_data["nid"] = st.text_input("NID নাম্বার")
                user_data["rider_id"] = st.text_input("গাড়ির নাম্বার (যেমন: Govt-1234)").upper()

            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if user_data.get("rider_id") and user_data.get("name"):
                    if register_user(user_data):
                        st.success(f"নিবন্ধন সফল! আপনার আইডি: {user_data['rider_id']}")
                        st.balloons()
                    else: st.error("এই আইডিটি ইতিমধ্যে ব্যবহৃত হয়েছে।")
                else: st.warning("নাম এবং আইডি প্রদান করা বাধ্যতামূলক।")

# --- ৬. পাম্প স্টেশন ইন্টারফেস ---
elif st.session_state.user_role == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False

    if not st.session_state.pump_auth:
        st.title("🏢 Pump Station Login")
        pin_in = st.text_input("ডেইলি পিন দিন", type="password")
        if st.button("Login"):
            if pin_in == CURRENT_DAILY_PIN:
                st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
    else:
        st.title("⛽ Pump Operation Panel")
        p_id = st.text_input("ইউজার আইডি সার্চ করুন")
        if p_id:
            user = get_rider_by_id(p_id)
            if user:
                st.subheader(f"👤 ইউজার: {user['name']} | ক্যাটাগরি: {user['category']}")
                
                # লক চেক
                eligible = True
                is_exempt = user.get('category') in ['Farmer (কৃষক)', 'Govt Emergency (সরকারি জরুরি সেবা)']
                
                if not is_exempt and user['last_refill']:
                    unlock_time = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock_time:
                        eligible = False; st.error(f"🚫 সাধারণ ইউজার হিসেবে আপনি লকড।")
                
                if eligible:
                    st.success("✅ তেল প্রদানের অনুমতি আছে")
                    col_x, col_y = st.columns(2)
                    with col_x:
                        f_type = st.selectbox("জ্বালানির ধরন", ["Octane", "Petrol", "Diesel"])
                        liters = st.number_input("লিটার পরিমাণ", 1.0, 500.0, 5.0)
                        if st.button("💾 ডাটা সেভ করুন"):
                            update_refill(user['rider_id'], liters, f_type, st.session_state.get("photo"))
                            st.success("সেভ হয়েছে!"); st.rerun()
                    with col_y:
                        photo = st.camera_input("ছবি (ঐচ্ছিক)")
                        if photo: st.session_state.photo = photo
            else: st.warning("ইউজার পাওয়া যায়নি।")
