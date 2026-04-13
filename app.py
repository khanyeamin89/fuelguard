import streamlit as st
from supabase import create_client, Client
from datetime import datetime, timedelta
import re
import qrcode
from io import BytesIO
import easyocr
import numpy as np
from PIL import Image
from streamlit_qrcode_scanner import qrcode_scanner

# --- ১. কনফিগারেশন ও সিএসএস ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; height: 3em; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

try:
    # আপনার সুপাবেস ক্রেডেনশিয়ালস
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except Exception as e:
    st.error("Configuration Error! Please check your Streamlit Secrets.")
    st.stop()

# কনস্ট্যান্ট ডাটা
LOCKOUT_HOURS = 72
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]
BN_EN_MAP = {"ঢাকা": "DHAKA", "চট্ট": "CHATTOGRAM", "মেট্রো": "METRO", "মেত্র": "METRO", "চট্র": "CHATTOGRAM", "ক": "KA", "খ": "KHA", "গ": "GA", "হ": "HA", "ল": "LA"}

# --- ২. ব্যাকএন্ড ও এআই ফাংশন ---
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['bn', 'en'])

def process_ai_image(image_file):
    reader = get_ocr_reader()
    results = reader.readtext(np.array(Image.open(image_file)))
    raw_text = " ".join([res[1] for res in results])
    processed = raw_text
    for bn, en in BN_EN_MAP.items():
        processed = processed.replace(bn, en)
    # শুধু ইংরেজি অক্ষর ও সংখ্যা রাখা হচ্ছে
    return re.sub(r'[^A-Z0-9]', '', processed.upper()), raw_text

def mask_name(name):
    if not name: return ""
    parts = name.split()
    return " ".join([p[:2] + "*" * (len(p)-2) if len(p) > 2 else p[0] + "*" for p in parts])

def generate_qr(data):
    qr = qrcode.QRCode(box_size=10, border=5)
    qr.add_data(data); qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf)
    return buf.getvalue()

def get_user_by_id(search_id):
    target = re.sub(r'[^A-Z0-9]', '', str(search_id).upper())
    try:
        res = supabase.table("riders").select("*").execute()
        for r in res.data:
            db_id = re.sub(r'[^A-Z0-9]', '', str(r['rider_id']).upper())
            if target in db_id or db_id in target: return r
        return None
    except: return None

# --- ৩. পপ-আপ ডায়ালগ ---
@st.dialog("✅ রেজিস্ট্রেশন সফল!")
def registration_success(rider_id):
    st.balloons()
    st.success(f"আপনার আইডি: {rider_id}")
    qr_img = generate_qr(rider_id)
    st.image(qr_img, width=200, caption="এই QR কোডটি সেভ করে রাখুন")
    st.download_button("QR ডাউনলোড করুন", qr_img, file_name=f"FuelQR_{rider_id}.png", use_container_width=True)
    if st.button("ঠিক আছে", use_container_width=True): st.rerun()

@st.dialog("⚠️ রিফিল কনফার্ম করুন")
def confirm_refill_popup(data):
    st.warning(f"আপনি কি **{data['name']}**-কে জ্বালানি দিচ্ছেন?")
    col1, col2 = st.columns(2)
    if col1.button("হ্যাঁ, নিশ্চিত", type="primary"):
        update_data = {"last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "liters": data['liters'], "fuel_type": data['type']}
        supabase.table("riders").update(update_data).eq("rider_id", data['id']).execute()
        st.success("সফলভাবে আপডেট করা হয়েছে!"); st.rerun()
    if col2.button("না, বাতিল"): st.rerun()

# --- ৪. ইউজার ইন্টারফেস (UI) ---
if "app_mode" not in st.session_state: st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro")
    st.subheader("আপনার ক্যাটাগরি বেছে নিন")
    c1, c2 = st.columns(2)
    if c1.button("🚜 কৃষক (Farmer)"): st.session_state.app_mode = "Farmer"; st.rerun()
    if c2.button("🚑 সরকারি (Govt)"): st.session_state.app_mode = "Govt"; st.rerun()
    if c1.button("🏍️ সাধারণ (General)"): st.session_state.app_mode = "General"; st.rerun()
    if c2.button("🏢 পাম্প অপারেটর", type="primary"): st.session_state.app_mode = "Pump"; st.rerun()
    st.stop()

# পোর্টাল লজিক
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ প্রধান পাতায়"): st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    st.title(f"👤 {mode} পোর্টাল")
    t1, t2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])
    
    with t1:
        method = st.radio("সার্চ পদ্ধতি:", ["ম্যানুয়াল/QR", "AI প্লেট স্ক্যান"], horizontal=True)
        target_id = ""
        if method == "ম্যানুয়াল/QR":
            target_id = st.text_input("আইডি বা নম্বর টাইপ করুন")
            if st.button("QR স্ক্যান করুন"):
                scanned = qrcode_scanner(key='user_scan')
                if scanned: target_id = scanned
        else:
            cam = st.camera_input("নাম্বার প্লেটের ছবি তুলুন")
            if cam:
                with st.spinner("AI বিশ্লেষণ করছে..."):
                    target_id, raw = process_ai_image(cam)
                    st.info(f"শনাক্তকৃত: {raw}")

        if target_id:
            user = get_user_by_id(target_id)
            if user:
                st.success(f"স্বাগতম, **{mask_name(user['name'])}**")
                st.image(generate_qr(user['rider_id']), width=150)
                if user['category'] == "General" and user['last_refill']:
                    unlock = datetime.strptime(user['last_refill'], "%Y-%m-%d %H:%M:%S") + timedelta(hours=LOCKOUT_HOURS)
                    if datetime.now() < unlock: st.error(f"🚫 লক! তেল পাবেন: {unlock.strftime('%b %d, %I:%M %p')}")
            else: st.error("তথ্য পাওয়া যায়নি।")

    with t2:
        with st.form("reg_form", clear_on_submit=True):
            u_name = st.text_input("আবেদনকারীর নাম")
            if mode == "Farmer":
                u_nid = st.text_input("NID নম্বর")
                u_cert = st.text_input("UNO/কৃষি কর্মকর্তা সার্টিফিকেট নং")
                final_id = f"FARM-{u_nid}".upper()
            elif mode == "Govt":
                u_office = st.text_input("অফিস আইডি (Office ID)")
                c1, c2, c3 = st.columns(3)
                dist = c1.selectbox("জেলা", BD_DISTRICTS, key="g_dist")
                ser = c2.selectbox("সিরিজ", SERIES_LIST, key="g_ser")
                num = c3.text_input("নম্বর (উদা: ১২-৩৪৫৬)", key="g_num")
                final_id = f"{dist}-{ser}-{num}".upper()
            else:
                c1, c2, c3 = st.columns(3)
                dist = c1.selectbox("জেলা", BD_DISTRICTS, key="gen_dist")
                ser = c2.selectbox("সিরিজ", SERIES_LIST, key="gen_ser")
                num = c3.text_input("নম্বর", key="gen_num")
                final_id = f"{dist}-{ser}-{num}".upper()

            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if u_name and final_id:
                    try:
                        payload = {"name": u_name, "rider_id": final_id, "category": mode}
                        if mode == "Farmer": payload["uno_cert"] = u_cert
                        if mode == "Govt": payload["office_id"] = u_office
                        
                        supabase.table("riders").insert(payload).execute()
                        registration_success(final_id)
                    except Exception as e:
                        if "duplicate" in str(e).lower(): st.error("এই আইডিটি ইতিমধ্যে সিস্টেমে আছে।")
                        else: st.error(f"ত্রুটি: {e}")

elif st.session_state.app_mode == "Pump":
    if st.sidebar.button("⬅️ প্রধান পাতায়"): st.session_state.app_mode = None; st.rerun()
    st.title("🏢 পাম্প অপারেটর প্যানেল")
    p_id = st.text_input("QR স্ক্যান বা আইডি লিখুন")
    if p_id:
        user = get_user_by_id(p_id)
        if user:
            st.info(f"ইউজার: {user['name']} ({user['category']})")
            f_type = st.selectbox("জ্বালানি", ["Petrol", "Octane", "Diesel"])
            liters = st.number_input("পরিমাণ (লিটার)", 1.0, 100.0, 5.0)
            if st.button("সেভ করুন", type="primary"):
                confirm_refill_popup({"id": user['rider_id'], "name": user['name'], "liters": liters, "type": f_type})
        else: st.error("ইউজার পাওয়া যায়নি।")
st.markdown("---")
st.caption("FuelGuard Pro 2026 | বাংলাদেশের মানুষের জন্য")
