import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import qrcode
import io

# --- ১. কনফিগারেশন ও কানেকশন ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

# Supabase Secrets (Streamlit Cloud Settings-এ এগুলো যোগ করুন)
try:
    URL = st.secrets["SUPABASE_URL"]
    KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(URL, KEY)
except Exception as e:
    st.error("Secrets missing! Please add SUPABASE_URL and SUPABASE_KEY in settings.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app" 

# ডেইলি পিন জেনারেটর (Base PIN + আজকের তারিখ)
def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    day_str = datetime.now().strftime("%d") 
    return f"{base_pin}{day_str}"

CURRENT_DAILY_PIN = get_daily_pin()

BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGANJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

# --- ২. ইউজার গাইড ডায়ালগ ---
@st.dialog("🚀 FuelGuard Pro: ইউজার গাইড")
def show_advanced_manual():
    st.markdown("""
    ### ⛽ নতুন সিস্টেম আপডেট:
    - **Rider Portal:** পিন ছাড়াই রেজিস্ট্রেশন ও স্ট্যাটাস চেক করা যাবে।
    - **Pump Station:** পাম্প অপারেটরদের জন্য প্রতিদিনের আলাদা পিন (Daily PIN) প্রয়োজন হবে।
    - **৭২ ঘণ্টা নিয়ম:** ডাটা এখন রিয়েল-টাইম ক্লাউড ডাটাবেজে সেভ হয়।
    """)
    if st.button("বুঝেছি, প্রবেশ করুন"):
        st.session_state.show_advanced_manual = False
        st.rerun()

if "show_advanced_manual" not in st.session_state:
    st.session_state.show_advanced_manual = True

if st.session_state.show_advanced_manual:
    show_advanced_manual()

# --- ৩. ডাটাবেজ ফাংশনসমূহ ---
def get_rider_by_id(rider_id):
    res = supabase.table("riders").select("*").eq("rider_id", rider_id.upper()).execute()
    return res.data[0] if res.data else None

def register_new_rider(rider_id, name):
    try:
        supabase.table("riders").insert({"rider_id": rider_id.upper(), "name": name, "liters": 0}).execute()
        return True
    except: return False

def update_refill_data(rider_id, liters, photo_file=None):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if photo_file:
        file_name = f"{rider_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        supabase.storage.from_("fuel_photos").upload(file_name, photo_file.getvalue())
    supabase.table("riders").update({"last_refill": now, "liters": float(liters)}).eq("rider_id", rider_id).execute()

# --- ৪. রোল সিলেকশন ---
if "user_role" not in st.session_state:
    st.session_state.user_role = None

if st.session_state.user_role is None:
    st.title("⛽ FuelGuard Pro")
    st.subheader("আপনার ভূমিকা নির্বাচন করুন:")
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
    if st.sidebar.button("⬅️ Home (Switch Role)"):
        st.session_state.user_role = None; st.rerun()
    
    st.title("🏍️ Rider Portal")
    t1, t2 = st.tabs(["🔍 চেক এলিজিবিলিটি", "📝 নতুন নিবন্ধন"])
    
    with t1:
        search_id = st.text_input("রেজিস্ট্রেশন নাম্বার (যেমন: PABNA HA 12-3456)")
        if search_id:
            rider = get_rider_by_id(search_id)
            if rider:
                st.info(f"👤 রাইডার: **{rider['name']}**")
                st.write(f"⛽ সর্বশেষ রিফিল: **{rider['liters']} লিটার**")
                if rider['last_refill']:
                    unlock = datetime.strptime(rider['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লকড! পরবর্তীতে পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ জ্বালানি পাওয়ার যোগ্য।")
                else: st.success("✅ জ্বালানি পাওয়ার যোগ্য।")
            else: st.warning("আইডি পাওয়া যায়নি।")

    with t2:
        with st.form("reg_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                d = st.selectbox("জেলা", sorted(BD_DISTRICTS)); s = st.selectbox("সিরিজ", SERIES_LIST)
            with col_b:
                n = st.text_input("নাম্বার (যেমন: 12-3456)"); nm = st.text_input("রাইডারের নাম")
            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if n and nm:
                    f_id = f"{d}-{s}-{n}".upper()
                    if register_new_rider(f_id, nm):
                        st.success(f"সফল! আইডি: {f_id}"); st.balloons()
                    else: st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")
                else: st.warning("সব তথ্য দিন।")

# --- ৬. পাম্প স্টেশন ইন্টারফেস ---
elif st.session_state.user_role == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False

    if not st.session_state.pump_auth:
        st.title("🏢 Pump Station Login")
        pin_in = st.text_input("আজকের ডেইলি পিন দিন", type="password")
        if st.button("Login"):
            if pin_in == CURRENT_DAILY_PIN:
                st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
        if st.button("⬅️ ব্যাক"): st.session_state.user_role = None; st.rerun()
    else:
        st.title("⛽ Pump Operation Panel")
        if st.sidebar.button("🚪 লগ আউট"):
            st.session_state.pump_auth = False; st.rerun()
            
        p_id = st.text_input("রাইডার আইডি (Scan/Type)")
        if p_id:
            rider = get_rider_by_id(p_id)
            if rider:
                st.write(f"👤 রাইডার: **{rider['name']}** | শেষ রিফিল: **{rider['liters']}L**")
                eligible = True
                if rider['last_refill']:
                    unlock_time = datetime.strptime(rider['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock_time:
                        eligible = False; st.error(f"🚫 লক করা! সময় বাকি।")
                if eligible:
                    st.success("✅ রিফিল অনুমোদিত")
                    c1, c2 = st.columns(2)
                    with c1:
                        liters = st.number_input("লিটার", 1.0, 100.0, 5.0)
                        if st.button("💾 Confirm & Save"):
                            update_refill_data(rider['rider_id'], liters, st.session_state.get("photo"))
                            st.success("সেভ হয়েছে!"); st.balloons(); st.rerun()
                    with c2:
                        photo = st.camera_input("গাড়ির ছবি (ঐচ্ছিক)")
                        if photo: st.session_state.photo = photo
            else: st.warning("আইডি পাওয়া যায়নি।")

# --- ৭. সাইডবার QR ---
if st.sidebar.checkbox("📥 QR Code Generator"):
    qr_id = st.sidebar.text_input("ID for QR")
    if qr_id:
        img = qrcode.make(f"{APP_URL}?rider={qr_id.upper()}")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.sidebar.image(buf.getvalue(), caption=qr_id)
