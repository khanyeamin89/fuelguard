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
    st.error("Secrets missing! Please add SUPABASE_URL and SUPABASE_KEY in Streamlit settings.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app" 

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    day_str = datetime.now().strftime("%d") 
    return f"{base_pin}{day_str}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. সাহায্যকারী ফাংশন (ID Cleaning) ---
def format_id_for_search(user_input):
    """ইউজার ইনপুট থেকে স্পেস ও ড্যাশ মুছে ফেলে বড় হাতের অক্ষরে রূপান্তর করে।"""
    if not user_input:
        return ""
    # স্পেস এবং ড্যাশ ডিলিট করা
    clean = re.sub(r'[-\s]', '', str(user_input))
    return clean.upper()

# --- ৩. ডাটাবেজ ফাংশনসমূহ ---
def get_rider_by_id(search_id):
    """
    ডাটাবেজে ড্যাশ থাকা সত্ত্বেও ড্যাশ ছাড়া সার্চ করার জন্য 
    আমরা PostgreSQL-এর replace ফাংশন ব্যবহার করছি।
    """
    clean_target = format_id_for_search(search_id)
    if not clean_target:
        return None
    
    try:
        # PostgreSQL কুয়েরি: ড্যাশ সরিয়ে চেক করা
        res = supabase.rpc('get_rider_by_clean_id', {'search_text': clean_target}).execute()
        
        # যদি RPC সেটআপ না থাকে, তবে সাধারণ পদ্ধতি (সব ডাটা এনে ফিল্টার - ছোট ডাটাবেজের জন্য কার্যকর)
        if not res.data:
            all_riders = supabase.table("riders").select("*").execute()
            for r in all_riders.data:
                if format_id_for_search(r['rider_id']) == clean_target:
                    return r
            return None
        return res.data[0]
    except:
        # ফেইলসেফ: যদি RPC না থাকে তবে সরাসরি ফিল্টার
        all_riders = supabase.table("riders").select("*").execute()
        for r in all_riders.data:
            if format_id_for_search(r['rider_id']) == clean_target:
                return r
        return None

def register_new_rider(rider_id, name):
    try:
        supabase.table("riders").insert({
            "rider_id": rider_id.upper().strip(),
            "name": name,
            "liters": 0
        }).execute()
        return True
    except: return False

def update_refill(rider_id, liters, photo_file=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if photo_file:
        file_name = f"{rider_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        supabase.storage.from_("fuel_photos").upload(file_name, photo_file.getvalue())
    
    supabase.table("riders").update({
        "last_refill": now,
        "liters": float(liters)
    }).eq("rider_id", rider_id).execute()

# --- ৪. রোল সিলেকশন ---
if "user_role" not in st.session_state:
    st.session_state.user_role = None

if st.session_state.user_role is None:
    st.title("⛽ FuelGuard Pro")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🏍️ Rider / Customer", use_container_width=True):
            st.session_state.user_role = "Rider"; st.rerun()
    with col2:
        if st.button("🏢 Pump Station", use_container_width=True):
            st.session_state.user_role = "Pump"; st.rerun()
    st.stop()

# --- ৫. রাইডার ইন্টারফেস ---
if st.session_state.user_role == "Rider":
    if st.sidebar.button("⬅️ Home"):
        st.session_state.user_role = None; st.rerun()
    
    st.title("🏍️ Rider Portal")
    tab1, tab2 = st.tabs(["🔍 চেক স্ট্যাটাস", "📝 নতুন নিবন্ধন"])
    
    with tab1:
        search_id = st.text_input("আইডি লিখুন (যেমন: PABNA HA 123456 বা PABNA-HA-12-3456)")
        if search_id:
            rider = get_rider_by_id(search_id)
            if rider:
                st.info(f"👤 রাইডার: **{rider['name']}**")
                st.write(f"🆔 আইডি: **{rider['rider_id']}**")
                st.write(f"⛽ শেষ রিফিল: **{rider['liters']} লিটার**")
                if rider['last_refill']:
                    unlock = datetime.strptime(rider['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লকড! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
            else: st.warning("এই আইডিটি নিবন্ধিত নয়।")

    with tab2:
        st.write("নতুন রাইডার নিবন্ধন করুন")
        with st.form("reg"):
            r_id = st.text_input("পুরো গাড়ির নাম্বার (যেমন: PABNA-HA-12-3456)")
            name = st.text_input("আপনার নাম")
            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if r_id and name:
                    if register_new_rider(r_id, name):
                        st.success(f"সফল! আপনার আইডি: {r_id.upper()}"); st.balloons()
                    else: st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")

# --- ৬. পাম্প স্টেশন ইন্টারফেস ---
elif st.session_state.user_role == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False

    if not st.session_state.pump_auth:
        st.title("🏢 Pump Station Login")
        pin_in = st.text_input("আজকের ডেইলি পিন দিন", type="password")
        if st.button("প্রবেশ করুন"):
            if pin_in == CURRENT_DAILY_PIN:
                st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
        if st.button("⬅️ ব্যাক"): st.session_state.user_role = None; st.rerun()
    else:
        st.title("⛽ Pump Operation Panel")
        p_id = st.text_input("আইডি সার্চ করুন (Case/Dash Sensitive নয়)")
        if p_id:
            rider = get_rider_by_id(p_id)
            if rider:
                st.subheader(f"👤 রাইডার: {rider['name']} ({rider['rider_id']})")
                eligible = True
                if rider['last_refill']:
                    unlock_time = datetime.strptime(rider['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock_time:
                        eligible = False; st.error(f"🚫 লক করা! সময় বাকি।")
                
                if eligible:
                    st.success("✅ রিফিল অনুমোদিত")
                    col_x, col_y = st.columns(2)
                    with col_x:
                        liters = st.number_input("লিটার পরিমাণ", 1.0, 100.0, 5.0)
                        if st.button("💾 ডাটা সেভ করুন"):
                            update_refill(rider['rider_id'], liters, st.session_state.get("taken_photo"))
                            st.success("সফলভাবে ক্লাউডে সেভ হয়েছে!"); st.balloons(); st.rerun()
                    with col_y:
                        photo = st.camera_input("গাড়ির ছবি (ঐচ্ছিক)")
                        if photo: st.session_state.taken_photo = photo
            else: st.warning("আইডি পাওয়া যায়নি।")

# --- ৭. QR জেনারেটর ---
st.sidebar.markdown("---")
if st.sidebar.checkbox("📥 QR Code Generator"):
    qr_id = st.sidebar.text_input("ID লিখুন")
    if qr_id:
        img = qrcode.make(f"{APP_URL}?rider={qr_id.upper()}")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.sidebar.image(buf.getvalue(), caption=f"QR for {qr_id}")
