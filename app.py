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
    st.error("Secrets missing! Please add SUPABASE_URL and SUPABASE_KEY in settings.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app" 

# জেলা এবং সিরিজের তালিকা
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGNJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    return f"{base_pin}{datetime.now().strftime('%d')}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. ডাটাবেজ ও আইডি ফাংশন ---
def format_id_for_search(user_input):
    if not user_input: return ""
    return re.sub(r'[-\s]', '', str(user_input)).upper()

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
    **স্বাগতম FuelGuard Pro-তে!**
    - **রেজিস্ট্রেশন:** জেলা, সিরিজ এবং নাম্বার দিয়ে সঠিকভাবে নিবন্ধন করুন।
    - **৭২ ঘণ্টা নিয়ম:** সাধারণ বাইকারদের জন্য ৩ দিনের লক প্রযোজ্য।
    - **বিশেষ ছাড়:** কৃষক ও জরুরি সেবার জন্য কোনো লক নেই।
    """)
    if st.button("ঠিক আছে"):
        st.session_state.seen_instruction = True; st.rerun()

if "seen_instruction" not in st.session_state:
    show_instruction()

# --- ৪. হোম পেজ (ক্যাটাগরি সিলেকশন) ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro: ক্যাটাগরি নির্বাচন করুন")
    st.markdown("---")
    col1, col2 = st.columns(2); col3, col4 = st.columns(2)
    with col1:
        if st.button("🚜 কৃষক / Farmer", use_container_width=True): st.session_state.app_mode = "Farmer"; st.rerun()
    with col2:
        if st.button("🚑 সরকারি জরুরি সেবা", use_container_width=True): st.session_state.app_mode = "Govt"; st.rerun()
    with col3:
        if st.button("🏍️ সাধারণ ব্যবহারকারী", use_container_width=True): st.session_state.app_mode = "General"; st.rerun()
    with col4:
        if st.button("🏢 পাম্প অপারেটর", use_container_width=True, type="primary"): st.session_state.app_mode = "Pump"; st.rerun()
    st.stop()

# --- ৫. ইউজার ইন্টারফেস ---
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ Home"): st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])

    with tab1:
        search_id = st.text_input("আপনার আইডি বা গাড়ির নাম্বার দিন")
        if search_id:
            user = get_user_by_id(search_id)
            if user:
                st.success(f"স্বাগতম, {user['name']}")
                st.write(f"ক্যাটাগরি: {user['category']} | সর্বশেষ: {user['liters']} লিটার")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                if is_exempt:
                    st.info("✅ আপনার জন্য ৭২ ঘণ্টার লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লক! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি তেল পাওয়ার যোগ্য।")

    with tab2:
        with st.form("reg_form"):
            reg_data = {"category": mode, "liters": 0, "last_refill": None}
            name = st.text_input("চালকের নাম")
            
            # --- সাধারণ ব্যবহারকারী ও সরকারি গাড়ির জন্য একই ফরম্যাট ---
            if mode in ["General", "Govt"]:
                c1, c2, c3 = st.columns(3)
                dist = c1.selectbox("জেলা", sorted(BD_DISTRICTS), key=f"dist_{mode}")
                ser = c2.selectbox("সিরিজ", SERIES_LIST, key=f"ser_{mode}")
                num = c3.text_input("নাম্বার (যেমন: 12-3456)", key=f"num_{mode}")
                
                # আইডি জেনারেশন (যেমন: DHAKA-METRO-GHA-11-2233)
                reg_data["rider_id"] = f"{dist}-{ser}-{num}".upper()
                
                if mode == "Govt":
                    reg_data["work_id"] = st.text_input("অফিসিয়াল ID নং / দপ্তরের নাম")
            
            # --- কৃষকদের জন্য আলাদা ফরম্যাট ---
            elif mode == "Farmer":
                reg_data["rider_id"] = st.text_input("NID নাম্বার")
                reg_data["uno_cert"] = st.text_input("UNO সার্টিফিকেট নং")

            reg_data["name"] = name
            
            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if name and (mode == "Farmer" or num):
                    try:
                        supabase.table("riders").insert(reg_data).execute()
                        st.success(f"নিবন্ধন সফল! আপনার আইডি: {reg_data['rider_id']}")
                        st.balloons()
                    except Exception as e:
                        st.error("এই গাড়িটি ইতিমধ্যে নিবন্ধিত অথবা ডাটাবেজে সমস্যা হয়েছে।")
                else:
                    st.warning("দয়া করে নাম এবং গাড়ির নম্বর সঠিকভাবে প্রদান করুন।")
# --- ৬. পাম্প অপারেটর ---
elif st.session_state.app_mode == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False
    if not st.session_state.pump_auth:
        pin = st.text_input("ডেইলি পিন দিন", type="password")
        if st.button("Login"):
            if pin == CURRENT_DAILY_PIN: st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
    else:
        p_id = st.text_input("আইডি সার্চ করুন")
        if p_id:
            user = get_user_by_id(p_id)
            if user:
                st.info(f"ইউজার: {user['name']} | {user['category']}")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                eligible = True
                if not is_exempt and user['last_refill']:
                    if datetime.now() < datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS):
                        eligible = False
                
                if eligible:
                    f_type = st.selectbox("টাইপ", ["Petrol", "Octane", "Diesel"])
                    liters = st.number_input("লিটার", 1.0, 100.0, 5.0)
                    if st.button("সেভ করুন"):
                        supabase.table("riders").update({
                            "last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "liters": float(liters), "fuel_type": f_type
                        }).eq("rider_id", user['rider_id']).execute()
                        st.success("সফল!"); st.rerun()
                else: st.error("🚫 ইউজার লকড!")

st.markdown("---")
st.caption("* বিশেষ ছাড়: কৃষক এবং সরকারি জরুরি সেবার ক্ষেত্রে '৭২ ঘণ্টার নিয়ম' প্রযোজ্য নয়।")
