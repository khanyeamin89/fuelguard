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

# গ্লোবাল ভেরিয়েবল
LOCKOUT_HOURS = 72
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

def get_daily_pin():
    base_pin = st.secrets.get("BASE_PIN", "1234")
    return f"{base_pin}{datetime.now().strftime('%d')}"

CURRENT_DAILY_PIN = get_daily_pin()

# --- ২. সাহায্যকারী ফাংশন (Smart Search) ---
def clean_id(text):
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

# --- ৩. পপ-আপ নির্দেশিকা ও কনফার্মেশন ডায়ালগ ---
@st.dialog("📖 FuelGuard Pro: ব্যবহারকারী নির্দেশিকা")
def show_instruction():
    st.markdown("""
    ### **স্বাগতম! অ্যাপটি ব্যবহারের নিয়মাবলী:**
    ---
    #### **১. ক্যাটাগরি ও শর্ত**
    * **আপনি নিজে এবং অন্য কারো eligibility চেক করতে পারবেন** 
    * ** খুব সহজেই নিবন্ধন করা যায়** 
    * **🚜 কৃষক ও 🚑 সরকারি:** আপনাদের জন্য কোনো সময়ের সীমাবদ্ধতা (Lock) নেই।
    * **🏍️ সাধারণ ব্যবহারকারী:** নিবন্ধনের পর রিফিলের ক্ষেত্রে **৭২ ঘণ্টা লক** প্রযোজ্য।
    #### **২. স্মার্ট সার্চ**
    * সার্চ করার সময় বড়/ছোট হাতের অক্ষর বা ড্যাশ (-) নিয়ে চিন্তা করতে হবে না।
    ---
    💡 *সঠিক তথ্য প্রদান করে আমাদের সহযোগিতা করুন।*
    """)
    if st.button("বুঝেছি, অ্যাপে প্রবেশ করুন", use_container_width=True, type="primary"):
        st.session_state.seen_instruction = True; st.rerun()

@st.dialog("⚠️ তথ্য নিশ্চিত করুন")
def confirm_refill_dialog():
    data = st.session_state.temp_refill_data
    st.write(f"আপনি কি নিশ্চিত যে **{data['rider_name']}**-কে **{data['liters']} লিটার {data['fuel_type']}** দিচ্ছেন?")
    st.warning("একবার সেভ করলে ডাটাবেজে তথ্য স্থায়ীভাবে সংরক্ষিত হবে।")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("হ্যাঁ, সেভ করুন", use_container_width=True, type="primary"):
            update_vals = {"last_refill": data["last_refill"], "liters": data["liters"], "fuel_type": data["fuel_type"]}
            if data["photo"]:
                f_name = f"{data['rider_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                supabase.storage.from_("fuel_photos").upload(f_name, data["photo"])
            supabase.table("riders").update(update_vals).eq("rider_id", data['rider_id']).execute()
            st.session_state.show_confirm_dialog = False
            st.success("সফলভাবে সংরক্ষিত!"); st.rerun()
    with col2:
        if st.button("না, বাতিল", use_container_width=True):
            st.session_state.show_confirm_dialog = False; st.rerun()

# --- ৪. ইনিশিয়ালাইজেশন ---
if "seen_instruction" not in st.session_state:
    show_instruction()
if "app_mode" not in st.session_state:
    st.session_state.app_mode = None
if st.session_state.get("show_confirm_dialog"):
    confirm_refill_dialog()

# --- ৫. হোম পেজ ---
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

# --- ৬. ইউজার পোর্টাল ---
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ প্রধান পাতায় ফিরুন"):
        st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    st.title(f"👤 {mode} পোর্টাল")
    tab1, tab2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])

    with tab1:
        s_id = st.text_input("আইডি বা গাড়ির নাম্বার দিন")
        if s_id:
            user = get_user_by_id(s_id)
            if user:
                st.success(f"স্বাগতম, **{user['name'].title()}**")
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                if is_exempt: st.info("✅ আপনার জন্য কোনো লক প্রযোজ্য নয়।")
                elif user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock: st.error(f"🚫 লক! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
                    else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
                else: st.success("✅ আপনি এখন তেল পাওয়ার যোগ্য।")
            else: st.warning("আইডি পাওয়া যায়নি।")

    with tab2:
        with st.form("reg_form"):
            name_input = st.text_input("পুরো নাম")
            reg_data = {"category": mode, "liters": 0, "last_refill": None}
            if mode in ["General", "Govt"]:
                c_d, c_s, c_n = st.columns(3)
                dist = c_d.selectbox("জেলা", sorted(BD_DISTRICTS))
                ser = c_s.selectbox("সিরিজ", SERIES_LIST)
                v_num = c_n.text_input("নাম্বার (উদা: 12-3456)")
                reg_data["rider_id"] = f"{dist}-{ser}-{v_num}".upper()
            else:
                reg_data["rider_id"] = st.text_input("NID নাম্বার")
                reg_data["uno_cert"] = st.text_input("UNO সার্টিফিকেট নম্বর")

            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if name_input and reg_data["rider_id"]:
                    reg_data["name"] = name_input.strip().title()
                    try:
                        supabase.table("riders").insert(reg_data).execute()
                        st.success("নিবন্ধন সফল!"); st.balloons()
                    except: st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")

# --- ৭. পাম্প অপারেটর প্যানেল ---
elif st.session_state.app_mode == "Pump":
    if "pump_auth" not in st.session_state: st.session_state.pump_auth = False
    if st.session_state.pump_auth and st.sidebar.button("⬅️ প্রধান পাতায় ফিরুন"):
        st.session_state.pump_auth = False; st.session_state.app_mode = None; st.rerun()

    if not st.session_state.pump_auth:
        st.title("🏢 পাম্প স্টেশন লগইন")
        pin = st.text_input("সিক্রেট পিন", type="password")
        if st.button("লগইন", use_container_width=True, type="primary"):
            if pin == CURRENT_DAILY_PIN: st.session_state.pump_auth = True; st.rerun()
            else: st.error("ভুল পিন!")
    else:
        st.title("⛽ পাম্প অপারেশন")
        p_search = st.text_input("সার্চ করুন (আইডি বা নাম্বার)")
        if p_search:
            user = get_user_by_id(p_search)
            if user:
                eligible = False; unlock_time = None
                is_exempt = user.get('category') in ["Farmer", "Govt"]
                if is_exempt: eligible = True
                elif user['last_refill']:
                    unlock_time = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    eligible = datetime.now() >= unlock_time
                else: eligible = True

                st.info(f"ইউজার: **{user['name'].title()}** | ক্যাটাগরি: {user['category']}")
                if eligible:
                    st.success("✅ রিফিল অনুমোদিত")
                    with st.container(border=True):
                        c_i, col_p = st.columns(2)
                        with c_i:
                            f_type = st.selectbox("জ্বালানি", ["Petrol", "Octane", "Diesel"])
                            liters = st.number_input("লিটার (১-১০০)", 1.0, 100.0, 5.0)
                        with col_p: photo = st.camera_input("ছবি (ঐচ্ছিক)")
                        
                        if st.button("💾 ডাটা সেভ করুন", use_container_width=True, type="primary"):
                            st.session_state.temp_refill_data = {
                                "last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "liters": float(liters), "fuel_type": f_type,
                                "rider_id": user['rider_id'], "rider_name": user['name'].title(),
                                "photo": photo.getvalue() if photo else None
                            }
                            st.session_state.show_confirm_dialog = True; st.rerun()
                else: st.error(f"🚫 ইউজার লকড! পুনরায় তেল পাবেন: {unlock_time.strftime('%b %d, %I:%M %p')}")
            else: st.error("আইডি পাওয়া যায়নি।")

st.markdown("---")
st.caption("* FuelGuard Pro - উন্নত ও নিরাপদ জ্বালানি বন্টন ব্যবস্থা।")
