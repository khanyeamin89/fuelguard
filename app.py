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
    ১. **কৃষক:** নিবন্ধনের জন্য NID এবং UNO সার্টিফিকেট নম্বর প্রয়োজন।
    ২. **অপারেটর:** তেল দেওয়ার সময় ছবি তোলা ঐচ্ছিক, তবে তথ্য সেভ করা বাধ্যতামূলক।
    ৩. **নিরাপত্তা:** প্রতিদিনের পিন ব্যবহার করে অপারেটর প্যানেলে প্রবেশ করুন।
    """)
    if st.button("ঠিক আছে"):
        st.session_state.seen_instruction = True; st.rerun()

if "seen_instruction" not in st.session_state:
    show_instruction()

# --- ৪. হোম পেজ ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro: ক্যাটাগরি নির্বাচন করুন")
    c1, c2 = st.columns(2); c3, c4 = st.columns(2)
    with c1:
        if st.button("🚜 কৃষক / Farmer", use_container_width=True): st.session_state.app_mode = "Farmer"; st.rerun()
    with c2:
        if st.button("🚑 সরকারি জরুরি সেবা", use_container_width=True): st.session_state.app_mode = "Govt"; st.rerun()
    with c3:
        if st.button("🏍️ সাধারণ ব্যবহারকারী", use_container_width=True): st.session_state.app_mode = "General"; st.rerun()
    with c4:
        if st.button("🏢 পাম্প অপারেটর", use_container_width=True, type="primary"): st.session_state.app_mode = "Pump"; st.rerun()
    st.stop()

# --- ৫. ইউজার পোর্টাল ---
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ Home"): st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])

    with tab1:
        search_id = st.text_input("আইডি বা গাড়ির নাম্বার দিন")
        if search_id:
            user = get_user_by_id(search_id)
            if user:
                st.success(f"স্বাগতম, **{user['name']}**")
                if user.get('category') in ["Farmer", "Govt"]:
                    st.info("✅ আপনার জন্য লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লক! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")

    # --- ৫. ইউজার ইন্টারফেস (User Portal) অংশ ---
with tab2:
    with st.form("reg_form"):
        reg_data = {"category": mode, "liters": 0, "last_refill": None}
        name = st.text_input("চালকের নাম / কর্মকর্তার নাম")
        
        # সরকারি গাড়ির জন্য বিশেষ ইনপুট
        if mode == "Govt":
            # জেলা, সিরিজ ও নাম্বারের ব্যবস্থা
            c1, c2, c3 = st.columns(3)
            dist = c1.selectbox("জেলা", sorted(BD_DISTRICTS), key="dist_govt")
            ser = c2.selectbox("সিরিজ", SERIES_LIST, key="ser_govt")
            num = c3.text_input("গাড়ির নাম্বার (উদা: 12-3456)", key="num_govt")
            
            reg_data["rider_id"] = f"{dist}-{ser}-{num}".upper()
            
            # অফিস আইডি বা দপ্তরের নাম (বাধ্যতামূলক)
            reg_data["work_id"] = st.text_input("অফিস আইডি (Office ID) / দপ্তরের নাম", placeholder="যেমন: LGED123 বা শিক্ষা অধিদপ্তর")
            st.info("🚑 সরকারি জরুরি সেবার গাড়ির ক্ষেত্রে ৭২ ঘণ্টার লক প্রযোজ্য হবে না।")

        # সাধারণ ব্যবহারকারী (Shadharon)
        elif mode == "General":
            c1, c2, c3 = st.columns(3)
            dist = c1.selectbox("জেলা", sorted(BD_DISTRICTS), key="dist_gen")
            ser = c2.selectbox("সিরিজ", SERIES_LIST, key="ser_gen")
            num = c3.text_input("নাম্বার", key="num_gen")
            reg_data["rider_id"] = f"{dist}-{ser}-{num}".upper()

        # কৃষক (Farmer)
        elif mode == "Farmer":
            reg_data["rider_id"] = st.text_input("NID নাম্বার")
            reg_data["uno_cert"] = st.text_input("UNO সার্টিফিকেট নম্বর")

        reg_data["name"] = name
        
        if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
            # ভ্যালিডেশন: সরকারি গাড়ির জন্য গাড়ির নম্বর এবং অফিস আইডি বাধ্যতামূলক
            is_valid = False
            if mode == "Govt":
                if name and num and reg_data.get("work_id"):
                    is_valid = True
            elif mode == "General":
                if name and num:
                    is_valid = True
            elif mode == "Farmer":
                if name and reg_data.get("rider_id") and reg_data.get("uno_cert"):
                    is_valid = True
            
            if is_valid:
                try:
                    supabase.table("riders").insert(reg_data).execute()
                    st.success(f"সফল! {mode} হিসেবে নিবন্ধিত হয়েছে। আইডি: {reg_data['rider_id']}")
                    st.balloons()
                except:
                    st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")
            else:
                st.warning("দয়া করে নাম, আইডি এবং প্রয়োজনীয় সকল তথ্য প্রদান করুন।")

# --- ৬. পাম্প অপারেটর ---
elif st.session_state.app_mode == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False
    
    if not st.session_state.pump_auth:
        pin = st.text_input("ডেইলি পিন দিন", type="password")
        if st.button("Login"):
            if pin == CURRENT_DAILY_PIN: st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
    else:
        st.title("⛽ পাম্প অপারেশন")
        p_id = st.text_input("আইডি সার্চ করুন")
        if p_id:
            user = get_user_by_id(p_id)
            if user:
                st.info(f"ইউজার: {user['name']} | ক্যাটাগরি: {user['category']}")
                if user['category'] == "Farmer": st.warning(f"📄 UNO সার্টিফিকেট: {user.get('uno_cert')}")
                
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                eligible = True
                if not is_exempt and user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock: eligible = False
                
                if eligible:
                    st.success("✅ রিফিল অনুমোদিত")
                    col_i, col_p = st.columns(2)
                    with col_i:
                        f_type = st.selectbox("টাইপ", ["Petrol", "Octane", "Diesel"])
                        liters = st.number_input("লিটার", 1.0, 500.0, 5.0)
                    with col_p:
                        photo = st.camera_input("ছবি (ঐচ্ছিক)")
                    
                    if st.button("💾 ডাটা সেভ করুন"):
                        up_data = {"last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "liters": float(liters), "fuel_type": f_type}
                        if photo:
                            f_name = f"{user['rider_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            supabase.storage.from_("fuel_photos").upload(f_name, photo.getvalue())
                        supabase.table("riders").update(up_data).eq("rider_id", user['rider_id']).execute()
                        st.success("সেভ হয়েছে!"); st.rerun()
                else: st.error("🚫 ইউজার লকড!")
