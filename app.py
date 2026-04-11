import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
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

# গ্লোবাল ভেরিয়েবল
LOCKOUT_HOURS = 72
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    return f"{base_pin}{datetime.now().strftime('%d')}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. Case-Insensitive ও Smart Search ফাংশন ---
def clean_id(text):
    """আইডি থেকে স্পেস এবং ড্যাশ সরিয়ে বড় হাতের অক্ষরে রূপান্তর করে"""
    if not text: return ""
    return re.sub(r'[-\s]', '', str(text)).upper()

def get_user_by_id(search_id):
    target = clean_id(search_id)
    try:
        res = supabase.table("riders").select("*").execute()
        for r in res.data:
            if clean_id(r['rider_id']) == target:
                return r
        return None
    except: return None

# --- ৩. তথ্যবহুল পপ-আপ নির্দেশিকা ---
@st.dialog("📖 FuelGuard Pro: ব্যবহারকারী নির্দেশিকা")
def show_instruction():
    st.markdown("""
    ### **স্বাগতম! অ্যাপটি ব্যবহারের নিয়মাবলী এক নজরে দেখে নিন:**
    ---
    #### **১. ব্যবহারকারীর ধরণ ও শর্ত (Categories)**
    * **🚜 কৃষক (Farmer):** নিবন্ধনের জন্য **NID** এবং **UNO সার্টিফিকেট** নম্বর প্রয়োজন। আপনাদের জন্য রিফিলের সময়ের কোনো সীমাবদ্ধতা নেই।
    * **🚑 সরকারি (Govt):** জরুরি সেবার যানবাহনের নিবন্ধনে **Office ID** প্রয়োজন। আপনাদের জন্যও ৭২ ঘণ্টার লক প্রযোজ্য নয়।
    * **🏍️ সাধারণ (General):** নিবন্ধনের জন্য সঠিক **গাড়ির নাম্বার** প্রদান বাধ্যতামূলক। 
    
    #### **২. রিফিল এবং লক (Rules)**
    * **৭২ ঘণ্টা নিয়ম:** সাধারণ রাইডাররা একবার তেল নেওয়ার পর পরবর্তী **৭২ ঘণ্টা** পর্যন্ত পুনরায় তেল নিতে পারবেন না। সার্চ করার সময় বড় বা ছোট হাতের অক্ষরের কোনো বাধ্যবাধকতা নেই।
    
    ---
    💡 *সঠিক তথ্য প্রদান করে ডিজিটাল জ্বালানি ব্যবস্থাপনায় সহায়তা করুন।*
    """)
    if st.button("বুঝেছি, অ্যাপে প্রবেশ করুন", use_container_width=True, type="primary"):
        st.session_state.seen_instruction = True
        st.rerun()

if "seen_instruction" not in st.session_state:
    show_instruction()

# --- ৪. হোম পেজ (ক্যাটাগরি সিলেকশন) ---
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro: ক্যাটাগরি নির্বাচন করুন")
    st.markdown("---")
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

# --- ৫. ইউজার পোর্টাল (Farmer, Govt, General) ---
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ প্রধান পাতায় ফিরুন"):
        st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    st.title(f"👤 {mode} পোর্টাল")
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])

    with tab1:
        s_id = st.text_input("আইডি বা গাড়ির নাম্বার দিন (বড়/ছোট হাত ম্যাটার করে না)")
        if s_id:
            user = get_user_by_id(s_id)
            if user:
                # নাম Title Case-এ দেখানো হচ্ছে
                st.success(f"স্বাগতম, **{user['name'].title()}**")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                if is_exempt:
                    st.info("✅ আপনার ক্যাটাগরিতে রিফিলের জন্য কোনো লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock:
                        st.error(f"🚫 লক! পুনরায় তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
            else: st.warning("আইডিটি পাওয়া যায়নি।")

    with tab2:
        with st.form("reg_form"):
            reg_data = {"category": mode, "liters": 0, "last_refill": None}
            name_input = st.text_input("আপনার পুরো নাম")
            v_num = "" 
            
            if mode in ["General", "Govt"]:
                c_d, c_s, c_n = st.columns(3)
                dist = c_d.selectbox("জেলা", sorted(BD_DISTRICTS), key=f"d_{mode}")
                ser = c_s.selectbox("সিরিজ", SERIES_LIST, key=f"s_{mode}")
                v_num = c_n.text_input("গাড়ির নাম্বার (উদা: 12-3456)", key=f"n_{mode}")
                reg_data["rider_id"] = f"{dist}-{ser}-{v_num}".upper()
                if mode == "Govt":
                    reg_data["work_id"] = st.text_input("অফিস আইডি বা দপ্তরের নাম")
            
            elif mode == "Farmer":
                reg_data["rider_id"] = st.text_input("NID নাম্বার")
                reg_data["uno_cert"] = st.text_input("UNO সার্টিফিকেট নম্বর")

            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                error = False
                if not name_input:
                    st.error("❌ নাম প্রদান করা বাধ্যতামূলক।"); error = True
                elif mode in ["General", "Govt"] and not v_num:
                    st.error("❌ গাড়ির নাম্বার প্রদান করা বাধ্যতামূলক।"); error = True
                elif mode == "Farmer" and (not reg_data["rider_id"] or not reg_data["uno_cert"]):
                    st.error("❌ NID এবং UNO সার্টিফিকেট নম্বর বাধ্যতামূলক।"); error = True
                
                if not error:
                    reg_data["name"] = name_input.strip().title()
                    try:
                        supabase.table("riders").insert(reg_data).execute()
                        st.success(f"নিবন্ধন সফল! আইডি: {reg_data['rider_id']}")
                        st.balloons()
                    except: st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")

# --- ৬. পাম্প অপারেটর প্যানেল ---
elif st.session_state.app_mode == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False
    
    if st.session_state.pump_auth:
        if st.sidebar.button("⬅️ প্রধান পাতায় ফিরুন"):
            st.session_state.pump_auth = False; st.session_state.app_mode = None; st.rerun()

    if not st.session_state.pump_auth:
        st.title("🏢 পাম্প স্টেশন লগইন")
        pin = st.text_input("সিক্রেট পিন দিন", type="password")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("লগইন", use_container_width=True, type="primary"):
                if pin == CURRENT_DAILY_PIN: st.session_state.pump_auth = True; st.rerun()
                else: st.error("ভুল পিন!")
        with c2:
            if st.button("⬅️ ব্যাক", use_container_width=True): st.session_state.app_mode = None; st.rerun()
    else:
        st.title("⛽ পাম্প অপারেশন")
        p_search = st.text_input("সার্চ (বড়/ছোট হাত বা স্পেস সমস্যা নেই)")
        if p_search:
            user = get_user_by_id(p_search)
            if user:
                st.info(f"ইউজার: {user['name'].title()} | ক্যাটাগরি: {user['category']}")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                eligible = True
                if not is_exempt and user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock: eligible = False
                
                if eligible:
                    st.success("✅ রিফিল অনুমোদিত")
                    c_i, col_p = st.columns(2)
                    with c_i:
                        f_type = st.selectbox("টাইপ", ["Petrol", "Octane", "Diesel"])
                        liters = st.number_input("লিটার", 1.0, 500.0, 5.0)
                    with col_p:
                        photo = st.camera_input("ছবি (ঐচ্ছিক)")
                    
                    if st.button("💾 ডাটা সেভ করুন", use_container_width=True, type="primary"):
                        update_vals = {"last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "liters": float(liters), "fuel_type": f_type}
                        if photo:
                            f_name = f"{user['rider_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                            supabase.storage.from_("fuel_photos").upload(f_name, photo.getvalue())
                        supabase.table("riders").update(update_vals).eq("rider_id", user['rider_id']).execute()
                        st.success("সফলভাবে সংরক্ষিত!"); st.rerun()
                else: st.error("🚫 ইউজার লকড!")
            else: st.error("আইডি পাওয়া যায়নি।")

st.markdown("---")
st.caption("* বিশেষ ছাড়: কৃষক এবং সরকারি জরুরি সেবার ক্ষেত্রে '৭২ ঘণ্টার নিয়ম' প্রযোজ্য নয়।")
