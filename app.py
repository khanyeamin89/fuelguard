import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import qrcode
import io
import re

# --- ১. কনফিগারেশন ও কানেকশন ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

# Supabase Secrets (Streamlit Cloud Settings-এ এগুলো যোগ করুন)
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Secrets missing! Please add SUPABASE_URL and SUPABASE_KEY in Streamlit settings.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app" 

# ডেইলি পিন জেনারেটর (Base PIN + আজকের তারিখ)
def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    day_str = datetime.now().strftime("%d") 
    return f"{base_pin}{day_str}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. সাহায্যকারী ফাংশন (ID Cleaning) ---
def format_id_for_search(user_input):
    if not user_input: return ""
    clean = re.sub(r'[-\s]', '', str(user_input))
    return clean.upper()

# --- ৩. পপ-আপ মেসেজ (Instruction Manual) ---
@st.dialog("📖 অ্যাপ ব্যবহারের নির্দেশিকা")
def show_instruction():
    st.markdown("""
    ### **FuelGuard Pro-তে আপনাকে স্বাগতম!**
    জ্বালানি বণ্টন ব্যবস্থা সহজ ও স্বচ্ছ করার জন্য এই অ্যাপটি তৈরি করা হয়েছে।
    
    **কিভাবে ব্যবহার করবেন?**
    1. **ক্যাটাগরি নির্বাচন:** আপনি কৃষক, সরকারি সেবা নাকি সাধারণ ইউজার—তা হোম পেজ থেকে বেছে নিন।
    2. **নতুন নিবন্ধন:** আপনি যদি আগে নিবন্ধিত না থাকেন, তবে 'নতুন নিবন্ধন' ট্যাবে গিয়ে তথ্য দিন।
    3. **৭২ ঘণ্টা নিয়ম:** সাধারণ ব্যবহারকারীদের জন্য একবার তেল নেওয়ার পর ৭২ ঘণ্টা পর্যন্ত লক থাকবে।
    4. **বিশেষ ছাড়:** কৃষক ও সরকারি জরুরি সেবার জন্য কোনো সময়ের নিষেধাজ্ঞা নেই।
    """)
    if st.button("ঠিক আছে, প্রবেশ করুন"):
        st.session_state.seen_instruction = True
        st.rerun()

if "seen_instruction" not in st.session_state:
    show_instruction()

# --- ৪. ডাটাবেজ ফাংশনসমূহ ---
def get_user_by_id(search_id):
    clean_target = format_id_for_search(search_id)
    try:
        # সব ইউজার এনে ফিল্টার করা (ছোট ডাটাবেজের জন্য কার্যকর)
        res = supabase.table("riders").select("*").execute()
        for r in res.data:
            if format_id_for_search(r['rider_id']) == clean_target:
                return r
        return None
    except: return None

def register_user(data):
    try:
        supabase.table("riders").insert(data).execute()
        return True
    except: return False

# --- ৫. স্টার্ট-আপ পেজ (Category Selection) ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro: আপনার ক্যাটাগরি নির্বাচন করুন")
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    c3, c4 = st.columns(2)

    with c1:
        if st.button("🚜 কৃষক / Farmer", use_container_width=True):
            st.session_state.app_mode = "Farmer"; st.rerun()
    with c2:
        if st.button("🚑 সরকারি জরুরি সেবা / Govt. Emergency", use_container_width=True):
            st.session_state.app_mode = "Govt"; st.rerun()
    with c3:
        if st.button("🏍️ সাধারণ ব্যবহারকারী / Shadharon", use_container_width=True):
            st.session_state.app_mode = "General"; st.rerun()
    with c4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏢 পাম্প অপারেটর / Pump Operator", use_container_width=True, type="primary"):
            st.session_state.app_mode = "Pump"; st.rerun()
    
    st.markdown("---")
    st.caption("* বিশেষ ছাড়: কৃষক এবং সরকারি জরুরি সেবার ক্ষেত্রে '৭২ ঘণ্টার নিয়ম' প্রযোজ্য নয়। তারা জরুরি প্রয়োজনে যেকোনো সময় তেল সংগ্রহ করতে পারবেন।")
    st.stop()

# --- ৬. ইউজার ইন্টারফেস (Farmer, Govt, General) ---
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ প্রধান পাতায় ফিরুন"):
        st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    st.title(f"👤 {mode} পোর্টাল")
    
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস ও হিস্ট্রি", "📝 নতুন নিবন্ধন"])

    with tab1:
        search_id = st.text_input("আইডি বা গাড়ির নাম্বার দিয়ে সার্চ করুন (যেমন: 123456)")
        if search_id:
            user = get_user_by_id(search_id)
            if user:
                st.success(f"স্বাগতম, **{user['name']}**")
                st.write(f"📊 ক্যাটাগরি: **{user.get('category')}**")
                
                c_a, c_b, c_c = st.columns(3)
                c_a.metric("সর্বশেষ রিফিল", f"{user['liters']} L")
                c_b.metric("জ্বালানির ধরন", user.get('fuel_type', 'N/A'))
                c_c.metric("তারিখ", user['last_refill'][:10] if user['last_refill'] else "N/A")
                
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                if is_exempt:
                    st.info("✅ আপনি বিশেষ ক্যাটাগরিতে আছেন। আপনার জন্য ৭২ ঘণ্টার লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লকড! পুনরায় তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
            else: st.warning("আইডি পাওয়া যায়নি।")

    with tab2:
        with st.form("registration_form"):
            reg_data = {"category": mode, "liters": 0, "last_refill": None}
            st.subheader(f"{mode} নিবন্ধন ফরম")
            
            if mode == "Farmer":
                reg_data["name"] = st.text_input("কৃষকের নাম")
                reg_data["address"] = st.text_input("ঠিকানা (গ্রাম/উপজেলা)")
                reg_data["rider_id"] = st.text_input("NID নাম্বার (এটিই লগইন আইডি)")
                reg_data["uno_cert"] = st.text_input("UNO সার্টিফিকেট নং")
            
            elif mode == "Govt":
                reg_data["name"] = st.text_input("চালকের নাম")
                reg_data["workplace"] = st.text_input("দপ্তরের নাম")
                reg_data["work_id"] = st.text_input("অফিসিয়াল ID নং")
                reg_data["rider_id"] = st.text_input("গাড়ির নাম্বার").upper()
            
            elif mode == "General":
                reg_data["name"] = st.text_input("আপনার নাম")
                reg_data["rider_id"] = st.text_input("গাড়ির নাম্বার (যেমন: PABNA-HA-1234)").upper()

            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if reg_data.get("rider_id") and reg_data.get("name"):
                    if register_user(reg_data):
                        st.success(f"সফল! আইডি: {reg_data['rider_id']}"); st.balloons()
                    else: st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")

    st.markdown("---")
    st.caption("* বিশেষ ছাড়: কৃষক এবং সরকারি জরুরি সেবার ক্ষেত্রে '৭২ ঘণ্টার নিয়ম' প্রযোজ্য নয়।")

# --- ৭. পাম্প অপারেটর ইন্টারফেস ---
elif st.session_state.app_mode == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False
    
    if not st.session_state.pump_auth:
        st.title("🏢 পাম্প স্টেশন লগইন")
        pin = st.text_input("আজকের ডেইলি পিন দিন", type="password")
        if st.button("প্রবেশ করুন"):
            if pin == CURRENT_DAILY_PIN:
                st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন! প্রতিদিনের পিন আলাদা হয়।")
        if st.button("⬅️ ব্যাক"): st.session_state.app_mode = None; st.rerun()
    else:
        st.title("⛽ পাম্প অপারেশন প্যানেল")
        if st.sidebar.button("🚪 লগ আউট"):
            st.session_state.pump_auth = False; st.rerun()
            
        p_id = st.text_input("ইউজার আইডি সার্চ করুন")
        if p_id:
            user = get_user_by_id(p_id)
            if user:
                st.info(f"ইউজার: {user['name']} | ক্যাটাগরি: {user['category']}")
                
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                eligible = True
                if not is_exempt and user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock: eligible = False
                
                if eligible:
                    st.success("✅ তেল প্রদানের অনুমতি আছে")
                    col_x, col_y = st.columns(2)
                    with col_x:
                        f_type = st.selectbox("জ্বালানির ধরন", ["Petrol", "Octane", "Diesel"])
                        liters = st.number_input("লিটার", 1.0, 500.0, 5.0)
                        if st.button("💾 ডাটা সেভ করুন"):
                            supabase.table("riders").update({
                                "last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "liters": float(liters),
                                "fuel_type": f_type
                            }).eq("rider_id", user['rider_id']).execute()
                            st.success("সফলভাবে সেভ হয়েছে!"); st.rerun()
                    with col_y:
                        photo = st.camera_input("ছবি (ঐচ্ছিক)")
                else:
                    st.error("🚫 ইউজার বর্তমানে ৭২ ঘণ্টার নিষেধাজ্ঞায় আছেন।")
            else: st.warning("আইডি পাওয়া যায়নি।")

    st.markdown("---")
    st.caption("* বিশেষ ছাড়: কৃষক এবং সরকারি জরুরি সেবার ক্ষেত্রে '৭২ ঘণ্টার নিয়ম' প্রযোজ্য নয়।")
