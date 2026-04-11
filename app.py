import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import re

# --- 1. CONFIGURATION & SEO ---
st.set_page_config(
    page_title="ফুয়েলগার্ড প্রো | FuelGuard Pro", 
    page_icon="⛽", 
    layout="centered",
    menu_items={
        'About': "ফুয়েলগার্ড প্রো: বাংলাদেশী নাগরিকদের জন্য উন্নত জ্বালানি বন্টন ব্যবস্থাপনা।"
    }
)

# --- 2. THE BANGLA-ONLY POP-UP DIALOG ---
@st.dialog("ব্যবহার নির্দেশিকা (Instructions)")
def show_instructions():
    st.markdown("""
        ### ফুয়েলগার্ড প্রো-তে স্বাগতম! ⛽
        সঠিকভাবে অ্যাপটি ব্যবহার করতে নিচের ধাপগুলো অনুসরণ করুন:
        
        ১. **ক্যাটাগরি নির্বাচন:** প্রথমে আপনার ধরন (কৃষক, সাধারণ বা সরকারি) বেছে নিন।
        ২. **নিবন্ধন:** আপনি যদি নতুন ব্যবহারকারী হন, তবে এনআইডি (NID) বা গাড়ির প্লেট নম্বর দিয়ে রেজিস্ট্রেশন সম্পন্ন করুন।
        ৩. **যোগ্যতা যাচাই:** 'Check Status' ট্যাব থেকে দেখুন আপনি জ্বালানি নেওয়ার যোগ্য কিনা। 
        ৪. **৭২ ঘণ্টার নিয়ম:** মনে রাখবেন, প্রতিবার জ্বালানি নেওয়ার পর পরবর্তী ৭২ ঘণ্টা আপনার আইডি লক থাকবে।
        ৫. **পাম্প অপারেটর:** জ্বালানি নেওয়ার সময় আপনার আইডি বা প্লেট নম্বরটি অপারেটরকে দিন।
        
        *নিরাপদ জ্বালানি বন্টনে আমাদের সহযোগিতা করুন।*
    """)
    if st.button("ঠিক আছে, বুঝেছি"):
        st.session_state.seen_instructions = True
        st.rerun()

# --- 3. SESSION STATE & TRIGGER POP-UP ---
if "seen_instructions" not in st.session_state:
    st.session_state.seen_instructions = False

if not st.session_state.seen_instructions:
    show_instructions()

# --- 4. STYLING ---
hide_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
"""
st.markdown(hide_style, unsafe_allow_html=True)

# --- 5. CONNECTION ---
@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"কনফিগারেশন ত্রুটি: {e}")
        return None

supabase = init_connection()

# --- 6. CONSTANTS & HELPERS ---
LOCKOUT_HOURS = 72
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

def clean_id(text):
    return re.sub(r'[-\s]', '', str(text)).upper()

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    return f"{base_pin}{datetime.now().strftime('%d')}"

def check_eligibility(user):
    if user.get('category') in ["Farmer", "Govt"]:
        return True, "Exempt"
    if not user.get('last_refill'):
        return True, "New User"
    
    last_time = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S")
    unlock_time = last_time + timedelta(hours=LOCKOUT_HOURS)
    
    if datetime.now() < unlock_time:
        return False, unlock_time
    return True, "Ready"

# --- 7. NAVIGATION STATE ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None
if "pump_auth" not in st.session_state:
    st.session_state.pump_auth = False

# --- 8. MAIN UI ---
st.write("# FuelGuard Pro: স্মার্ট ফুয়েল বন্টন")
st.write("বাংলাদেশী নাগরিকদের জন্য ডিজিটাল জ্বালানি ব্যবস্থাপনা পোর্টাল।")

if st.session_state.app_mode:
    if st.sidebar.button("⬅️ প্রধান মেনুতে ফিরে যান"):
        st.session_state.app_mode = None
        st.session_state.pump_auth = False
        st.rerun()

# --- 9. MAIN MENU ---
if st.session_state.app_mode is None:
    st.subheader("আপনার ক্যাটাগরি নির্বাচন করুন")
    
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚜 কৃষক (Farmer)", use_container_width=True):
            st.session_state.app_mode = "Farmer"; st.rerun()
        if st.button("🏍️ সাধারণ (General)", use_container_width=True):
            st.session_state.app_mode = "General"; st.rerun()
    with c2:
        if st.button("🚑 সরকারি (Govt)", use_container_width=True):
            st.session_state.app_mode = "Govt"; st.rerun()
        if st.button("🏢 পাম্প অপারেটর (Operator)", use_container_width=True, type="primary"):
            st.session_state.app_mode = "Pump"; st.rerun()
    st.stop()

# --- 10. USER PORTALS ---
mode = st.session_state.app_mode
if mode in ["Farmer", "Govt", "General"]:
    st.title(f"{mode} পোর্টাল")
    tab1, tab2 = st.tabs(["🔍 তথ্য যাচাই (Check Status)", "📝 নিবন্ধন (Registration)"])

    with tab1:
        s_id = st.text_input("আইডি বা যানবাহনের প্লেট নম্বর দিন")
        if s_id:
            res = supabase.table("riders").select("*").eq("rider_id", clean_id(s_id)).execute()
            if res.data:
                user = res.data[0]
                eligible, detail = check_eligibility(user)
                st.info(f"ব্যবহারকারীর নাম: **{user['name']}**")
                if eligible:
                    st.success("✅ আপনি জ্বালানি সংগ্রহের জন্য যোগ্য।")
                else:
                    st.error(f"🚫 দুঃখিত! আপনার লক পিরিয়ড শেষ হবে: {detail.strftime('%b %d, %I:%M %p')}")
            else:
                st.warning("তথ্য পাওয়া যায়নি। অনুগ্রহ করে প্রথমে নিবন্ধন করুন।")

    with tab2:
        with st.form("reg_form"):
            name = st.text_input("পূর্ণ নাম (Full Name)")
            reg_id = ""
            extra_info = ""
            
            if mode == "Farmer":
                reg_id = st.text_input("এনআইডি (NID) নম্বর")
                extra_info = st.text_input("ইউ এন ও সার্টিফিকেট নম্বর")
            else:
                col1, col2, col3 = st.columns(3)
                dist = col1.selectbox("জেলা (District)", BD_DISTRICTS)
                ser = col2.selectbox("সিরিজ", SERIES_LIST)
                num = col3.text_input("নম্বর (12-3456)")
                reg_id = f"{dist}{ser}{num}"
                if mode == "Govt":
                    extra_info = st.text_input("অফিস বা দপ্তরের নাম")

            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if name and reg_id:
                    try:
                        payload = {
                            "rider_id": clean_id(reg_id),
                            "name": name.strip().title(),
                            "category": mode,
                            "liters": 0,
                            "extra_info": extra_info
                        }
                        supabase.table("riders").insert(payload).execute()
                        st.success("অভিনন্দন! আপনার নিবন্ধন সফল হয়েছে।")
                    except:
                        st.error("এই আইডি দিয়ে ইতিমধ্যে নিবন্ধন করা হয়েছে।")
                else:
                    st.error("অনুগ্রহ করে সকল তথ্য সঠিক ভাবে পূরণ করুন।")

# --- 11. PUMP OPERATOR ---
elif mode == "Pump":
    if not st.session_state.pump_auth:
        st.title("অপারেটর লগইন")
        pin = st.text_input("ডেইলি পিন (Daily PIN)", type="password")
        if st.button("লগইন"):
            if pin == get_daily_pin():
                st.session_state.pump_auth = True; st.rerun()
            else:
                st.error("পিন নম্বরটি সঠিক নয়।")
    else:
        st.title("স্টেশন অপারেশন")
        p_search = st.text_input("আইডি সার্চ বা স্ক্যান করুন")
        if p_search:
            res = supabase.table("riders").select("*").eq("rider_id", clean_id(p_search)).execute()
            if res.data:
                user = res.data[0]
                eligible, detail = check_eligibility(user)
                
                if eligible:
                    st.success(f"যাচাইকৃত: {user['name']}")
                    f_type = st.radio("জ্বালানির ধরন", ["অকটেন", "পেট্রোল", "ডিজেল"], horizontal=True)
                    amount = st.number_input("লিটার পরিমাণ", 1.0, 100.0, 5.0)
                    
                    if st.button("ট্রানজেকশন সেভ করুন"):
                        new_total = float(user.get('liters', 0)) + amount
                        update_vals = {
                            "last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "liters": new_total,
                            "fuel_type": f_type
                        }
                        supabase.table("riders").update(update_vals).eq("rider_id", user['rider_id']).execute()
                        st.success("সফলভাবে ট্রানজেকশন সেভ করা হয়েছে।")
                else:
                    st.error(f"প্রত্যাখ্যাত: ব্যবহারকারী লক অবস্থায় আছেন। সময়: {detail}")
            else:
                st.error("তথ্য পাওয়া যায়নি।")

st.markdown("---")
st.caption("ফুয়েলগার্ড প্রো © 2026 | বাংলাদেশে জ্বালানি বন্টন নিয়ন্ত্রণে নিয়োজিত।")
