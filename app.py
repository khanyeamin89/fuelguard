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

# জেলা ও সিরিজের তালিকা
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    return f"{base_pin}{datetime.now().strftime('%d')}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. সাহায্যকারী ফাংশন ---
def format_id_for_search(user_input):
    if not user_input: return ""
    clean = re.sub(r'[-\s]', '', str(user_input))
    return clean.upper()

def get_user_by_id(search_id):
    clean_target = format_id_for_search(search_id)
    try:
        res = supabase.table("riders").select("*").execute()
        for r in res.data:
            if format_id_for_search(r['rider_id']) == clean_target:
                return r
        return None
    except: return None

# --- ৩. পপ-আপ নির্দেশিকা ---
@st.dialog("📖 অ্যাপ ব্যবহারের নির্দেশিকা")
def show_instruction():
    st.markdown("""
    ### **FuelGuard Pro-তে স্বাগতম!**
    ১. **নিবন্ধন:** আপনার সঠিক ক্যাটাগরি অনুযায়ী নিবন্ধন সম্পন্ন করুন।
    ২. **পাম্প অপারেটর:** তেল প্রদানের সময় অবশ্যই মিটার বা গাড়ির ছবি তুলুন।
    ৩. **ছাড়:** কৃষক ও সরকারি গাড়ির জন্য কোনো লক টাইম নেই।
    """)
    if st.button("ঠিক আছে, প্রবেশ করুন"):
        st.session_state.seen_instruction = True
        st.rerun()

if "seen_instruction" not in st.session_state:
    show_instruction()

# --- ৪. হোম পেজ ---
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
        if st.button("🚑 সরকারি জরুরি সেবা", use_container_width=True):
            st.session_state.app_mode = "Govt"; st.rerun()
    with c3:
        if st.button("🏍️ সাধারণ ব্যবহারকারী", use_container_width=True):
            st.session_state.app_mode = "General"; st.rerun()
    with c4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🏢 পাম্প অপারেটর", use_container_width=True, type="primary"):
            st.session_state.app_mode = "Pump"; st.rerun()
    
    st.stop()

# --- ৫. ইউজার পোর্টাল ---
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ প্রধান পাতায় ফিরুন"):
        st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])

    with tab1:
        search_id = st.text_input("আইডি বা গাড়ির নাম্বার দিন")
        if search_id:
            user = get_user_by_id(search_id)
            if user:
                st.success(f"স্বাগতম, **{user['name']}**")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                if is_exempt:
                    st.info("✅ আপনার জন্য লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লক! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি তেল পাওয়ার যোগ্য।")

    with tab2:
        with st.form("reg_form"):
            reg_data = {"category": mode, "liters": 0, "last_refill": None}
            name = st.text_input("নাম")
            if mode in ["General", "Govt"]:
                col_d, col_s, col_n = st.columns(3)
                dist = col_d.selectbox("জেলা", sorted(BD_DISTRICTS), key=f"d_{mode}")
                ser = col_s.selectbox("সিরিজ", SERIES_LIST, key=f"s_{mode}")
                num = col_n.text_input("নাম্বার", key=f"n_{mode}")
                reg_data["rider_id"] = f"{dist}-{ser}-{num}".upper()
            elif mode == "Farmer":
                reg_data["rider_id"] = st.text_input("NID নাম্বার")
            reg_data["name"] = name
            if st.form_submit_button("নিবন্ধন করুন"):
                try:
                    supabase.table("riders").insert(reg_data).execute()
                    st.success("সফল!"); st.balloons()
                except: st.error("ইতিমধ্যে নিবন্ধিত!")

# --- ৬. পাম্প অপারেটর ---
elif st.session_state.app_mode == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False
    
    if not st.session_state.pump_auth:
        pin = st.text_input("ডেইলি পিন দিন", type="password")
        if st.button("Login"):
            if pin == CURRENT_DAILY_PIN: st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
    else:
        st.title("⛽ পাম্প অপারেশন প্যানেল")
        p_id = st.text_input("আইডি সার্চ করুন")
        if p_id:
            user = get_user_by_id(p_id)
            if user:
                st.info(f"রাইডার: {user['name']}")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                eligible = True
                if not is_exempt and user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock: eligible = False
                
                if eligible:
                    st.success("✅ রিফিল অনুমোদিত")
                    col_input, col_photo = st.columns(2)
                    with col_input:
                        f_type = st.selectbox("টাইপ", ["Petrol", "Octane", "Diesel"])
                        liters = st.number_input("লিটার", 1.0, 500.0, 5.0)
                    with col_photo:
                        photo = st.camera_input("গাড়ির/মিটারে ছবি")
                    
                    if st.button("💾 ডাটা সেভ করুন"):
                        update_data = {
                            "last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "liters": float(liters), "fuel_type": f_type
                        }
                        if photo:
                            f_name = f"{user['rider_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            supabase.storage.from_("fuel_photos").upload(f_name, photo.getvalue())
                        supabase.table("riders").update(update_data).eq("rider_id", user['rider_id']).execute()
                        st.success("সেভ হয়েছে!"); st.rerun()
                else: st.error("🚫 ইউজার লকড!")
