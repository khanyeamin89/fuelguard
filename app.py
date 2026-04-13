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

# --- ১. কনফিগারেশন ও কানেকশন ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

# কাস্টম CSS ফর বেটার UI
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #ffffff; border-radius: 8px 8px 0px 0px; padding: 10px 20px; }
    </style>
    """, unsafe_allow_html=True)

try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Supabase secrets missing!"); st.stop()

# ডাটাবেজ কনস্ট্যান্ট
BD_DISTRICTS = ["BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", "SYLHET METRO", "TANGAIL", "THAKURGAON"]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]
BN_EN_MAP = {"ঢাকা": "DHAKA", "চট্ট": "CHATTOGRAM", "মেট্রো": "METRO", "মেত্র": "METRO", "চট্র": "CHATTOGRAM", "ক": "KA", "খ": "KHA", "গ": "GA", "হ": "HA", "ল": "LA"}

# --- ২. সাহায্যকারী ফাংশনসমূহ ---
@st.cache_resource
def get_ocr_reader():
    return easyocr.Reader(['bn', 'en'])

def process_ai_image(image_file):
    reader = get_ocr_reader()
    results = reader.readtext(np.array(Image.open(image_file)))
    raw_text = " ".join([res[1] for res in results])
    processed = raw_text
    for bn, en in BN_EN_MAP.items(): processed = processed.replace(bn, en)
    return re.sub(r'[^A-Z0-9]', '', processed.upper()), raw_text

def generate_qr(data):
    qr = qrcode.QRCode(box_size=10, border=5)
    qr.add_data(data); qr.make(fit=True)
    buf = BytesIO()
    qr.make_image(fill_color="black", back_color="white").save(buf)
    return buf.getvalue()

def get_user_by_id(search_id):
    target = re.sub(r'[^A-Z0-9]', '', str(search_id).upper())
    res = supabase.table("riders").select("*").execute()
    for r in res.data:
        db_id = re.sub(r'[^A-Z0-9]', '', str(r['rider_id']).upper())
        if target in db_id or db_id in target: return r
    return None

# --- ৩. ডায়ালগসমূহ ---
@st.dialog("✅ রেজিস্ট্রেশন সফল!")
def registration_success(rider_id):
    st.balloons()
    st.success(f"সফলভাবে নিবন্ধিত! আইডি: {rider_id}")
    qr_img = generate_qr(rider_id)
    st.image(qr_img, width=200, caption="আপনার QR কোড")
    st.download_button("QR কোড ডাউনলোড করুন", qr_img, file_name=f"FuelQR_{rider_id}.png", use_container_width=True)
    if st.button("প্রধান পাতায় ফিরুন", use_container_width=True): st.rerun()

# --- ৪. মেইন অ্যাপ লজিক ---
if "app_mode" not in st.session_state: st.session_state.app_mode = None

# হোম স্ক্রিন UI
if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro")
    st.subheader("আপনার ক্যাটাগরি নির্বাচন করুন")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚜 কৃষক (Farmer)", type="secondary"): st.session_state.app_mode = "Farmer"; st.rerun()
        if st.button("🏍️ সাধারণ (General)", type="secondary"): st.session_state.app_mode = "General"; st.rerun()
    with col2:
        if st.button("🚑 সরকারি (Govt)", type="secondary"): st.session_state.app_mode = "Govt"; st.rerun()
        if st.button("🏢 পাম্প অপারেটর", type="primary"): st.session_state.app_mode = "Pump"; st.rerun()
    st.stop()

# ইউজার পোর্টাল UI
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ Home"): st.session_state.app_mode = None; st.rerun()
    
    mode = st.session_state.app_mode
    st.title(f"👤 {mode} পোর্টাল")
    
    t1, t2 = st.tabs(["🔍 স্ট্যাটাস চেক", "📝 নতুন নিবন্ধন"])
    
    with t1:
        method = st.radio("সার্চ পদ্ধতি:", ["ম্যানুয়াল/QR", "AI প্লেট স্ক্যান"], horizontal=True)
        target_id = ""
        if method == "ম্যানুয়াল/QR":
            target_id = st.text_input("আইডি বা গাড়ির নাম্বার")
            if st.button("QR স্ক্যানার চালু করুন"):
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
                st.success(f"হ্যালো, **{user['name']}**")
                st.image(generate_qr(user['rider_id']), width=150)
            else: st.error("তথ্য পাওয়া যায়নি।")

    with t2:
        st.subheader("নিবন্ধন ফরম")
        with st.form("reg_form", clear_on_submit=True):
            u_name = st.text_input("আবেদনকারীর পূর্ণ নাম")
            
            # ক্যাটাগরি অনুযায়ী ডায়নামিক ফিল্ড
            if mode == "Farmer":
                u_nid = st.text_input("এনআইডি (NID) নম্বর")
                u_cert = st.text_input("UNO / কৃষি কর্মকর্তার সার্টিফিকেট নম্বর")
                final_id = f"FARM-{u_nid}"
            elif mode == "Govt":
                u_office_id = st.text_input("অফিস আইডি নম্বর")
                c1, c2, c3 = st.columns(3)
                dist = c1.selectbox("জেলা", BD_DISTRICTS)
                ser = c2.selectbox("সিরিজ", SERIES_LIST)
                num = c3.text_input("গাড়ির নম্বর (১২-৩৪৫৬)")
                final_id = f"{dist}-{ser}-{num}".upper()
            else:
                c1, c2, c3 = st.columns(3)
                dist = c1.selectbox("জেলা", BD_DISTRICTS)
                ser = c2.selectbox("সিরিজ", SERIES_LIST)
                num = c3.text_input("গাড়ির নম্বর (১২-৩৪৫৬)")
                final_id = f"{dist}-{ser}-{num}".upper()
            
            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if u_name and final_id:
                    try:
                        data = {"name": u_name, "rider_id": final_id, "category": mode}
                        if mode == "Farmer": data["uno_cert"] = u_cert
                        elif mode == "Govt": data["office_id"] = u_office_id
                        
                        supabase.table("riders").insert(data).execute()
                        registration_success(final_id)
                    except: st.error("এই আইডিটি ইতিমধ্যে সিস্টেমে আছে।")
                else: st.warning("সবগুলো ফিল্ড সঠিকভাবে পূরণ করুন।")

# অপারেটর প্যানেল (Pump)
elif st.session_state.app_mode == "Pump":
    if st.sidebar.button("⬅️ Home"): st.session_state.app_mode = None; st.rerun()
    st.title("🏢 অপারেটর কন্ট্রোল প্যানেল")
    # অপারেটর লজিক (পূর্বের পিন ভেরিফিকেশন ও রিফিল লজিক এখানে থাকবে)
    st.info("এখানে পিন দিয়ে লগইন করে QR স্ক্যান করে তেল দেওয়ার অপশন থাকবে।")
