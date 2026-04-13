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

try:
    supabase: Client = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
except:
    st.error("Supabase secrets missing!"); st.stop()

# ৬৪ জেলার পূর্ণাঙ্গ তালিকা
BD_DISTRICTS = [
    "BAGERHAT", "BANDARBAN", "BARGUNA", "BARISHAL", "BHOLA", "BOGURA", "BRAHMANBARIA", "CHANDPUR", 
    "CHATTOGRAM", "CHATTOGRAM METRO", "CHUADANGA", "COMILLA", "COXS BAZAR", "DHAKA", "DHAKA METRO", 
    "DINAJPUR", "FARIDPUR", "FENI", "GAIBANDHA", "GAZIPUR", "GOPALGANJ", "HABIGANJ", "JAMALPUR", 
    "JASHORE", "JHALOKATHI", "JHENAIDAH", "JOYPURHAT", "KHAGRACHHARI", "KHULNA", "KHULNA METRO", 
    "KISHOREGNJ", "KURIGRAM", "KUSHTIA", "LAKSHMIPUR", "LALMONIRHAT", "MADARIPUR", "MAGURA", 
    "MANIKGANJ", "MEHERPUR", "MOULVIBAZAR", "MUNSHIGANJ", "MYMENSINGH", "NAOGAON", "NARAIL", 
    "NARAYANGANJ", "NARSINGDI", "NATORE", "NETROKONA", "NILPHAMARI", "NOAKHALI", "PABNA", 
    "PANCHAGARH", "PATUAKHALI", "PIROJPUR", "RAJBARI", "RAJSHAHI", "RAJSHAHI METRO", "RANGAMATI", 
    "RANGPUR", "SATKHIRA", "SHARIATPUR", "SHERPUR", "SIRAJGANJ", "SUNAMGANJ", "SYLHET", 
    "SYLHET METRO", "TANGAIL", "THAKURGAON"
]
SERIES_LIST = ["KA", "KHA", "GA", "GHA", "CHA", "THA", "HA", "LA", "MA", "BA"]

# বাংলা টু ইংরেজি ম্যাপ
BN_EN_MAP = {
    "ঢাকা": "DHAKA", "চট্ট": "CHATTOGRAM", "মেট্রো": "METRO", "মেত্র": "METRO",
    "চট্র": "CHATTOGRAM", "খুলনা": "KHULNA", "রাজশাহী": "RAJSHAHI", "সিলেট": "SYLHET",
    "ক": "KA", "খ": "KHA", "গ": "GA", "ঘ": "GHA", "চ": "CHA", "ছ": "CHA",
    "থ": "THA", "হ": "HA", "ল": "LA", "ম": "MA", "ব": "BA"
}

# --- ২. সাহায্যকারী ফাংশনসমূহ ---
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

# --- ৩. পপ-আপ ডায়ালগসমূহ ---

@st.dialog("📖 অ্যাপ ব্যবহার নির্দেশিকা")
def show_instruction():
    st.markdown("""
    ### **FuelGuard Pro-তে স্বাগতম!**
    ---
    * **AI Scan:** নাম্বার প্লেটের ছবি তুলে স্ট্যাটাস চেক করুন।
    * **QR Code:** রেজিস্ট্রেশন শেষে আপনার পার্সোনাল QR কোডটি সেভ করুন।
    * **Security:** সাধারণ রাইডারদের জন্য ৭২ ঘণ্টা লক প্রযোজ্য।
    """)
    if st.button("বুঝেছি, প্রবেশ করুন", use_container_width=True, type="primary"):
        st.session_state.seen_info = True; st.rerun()

@st.dialog("✅ রেজিস্ট্রেশন সফল!")
def registration_success(rider_id):
    st.balloons()
    st.success(f"সফলভাবে নিবন্ধিত! আপনার আইডি: {rider_id}")
    qr_img = generate_qr(rider_id)
    st.image(qr_img, width=200)
    st.download_button("QR ডাউনলোড করুন", qr_img, file_name=f"FuelQR_{rider_id}.png")
    if st.button("Home-এ ফিরুন"): st.rerun()

@st.dialog("⚠️ রিফিল নিশ্চিতকরণ")
def confirm_refill_dialog(data):
    st.warning(f"আপনি কি নিশ্চিত যে **{data['name']}**-কে জ্বালানি দিচ্ছেন?")
    st.write(f"পরিমাণ: {data['liters']}L | ধরণ: {data['type']}")
    c1, c2 = st.columns(2)
    if c1.button("হ্যাঁ, সেভ করুন", type="primary", use_container_width=True):
        update = {"last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "liters": data['liters'], "fuel_type": data['type']}
        supabase.table("riders").update(update).eq("rider_id", data['id']).execute()
        st.success("ডাটা সেভ হয়েছে!"); st.rerun()
    if c2.button("বাতিল", use_container_width=True): st.rerun()

# --- ৪. মেইন লজিক ---

if "seen_info" not in st.session_state:
    show_instruction()

if "app_mode" not in st.session_state:
    st.session_state.app_mode = None

if st.session_state.app_mode is None:
    st.title("⛽ FuelGuard Pro")
    cols = st.columns(4)
    btn_conf = [("🚜 Farmer", "Farmer"), ("🚑 Govt", "Govt"), ("🏍️ General", "General"), ("🏢 Operator", "Pump")]
    for i, (label, mode) in enumerate(btn_conf):
        if cols[i].button(label, use_container_width=True):
            st.session_state.app_mode = mode; st.rerun()
    st.stop()

# ইউজার পোর্টাল
if st.session_state.app_mode in ["Farmer", "Govt", "General"]:
    if st.sidebar.button("⬅️ Home"): st.session_state.app_mode = None; st.rerun()
    
    t1, t2 = st.tabs(["🔍 Status Check", "📝 Registration"])
    
    with t1:
        method = st.radio("Search Method:", ["Manual/QR", "AI Plate Scan"], horizontal=True)
        target_id = ""
        if method == "Manual/QR":
            target_id = st.text_input("ID/Number Plate লিখুন")
            scanned = qrcode_scanner(key='user_scan')
            if scanned: target_id = scanned
        else:
            cam = st.camera_input("নাম্বার প্লেটের ছবি তুলুন")
            if cam:
                with st.spinner("AI বিশ্লেষণ করছে..."):
                    target_id, raw = process_ai_image(cam)
                    st.info(f"AI শনাক্ত করেছে: {raw}")

        if target_id:
            user = get_user_by_id(target_id)
            if user:
                st.success(f"হ্যালো, **{user['name']}**")
                st.image(generate_qr(user['rider_id']), width=150)
            else: st.error("কোনো তথ্য পাওয়া যায়নি।")

    with t2:
        with st.form("reg_form"):
            u_name = st.text_input("পূর্ণ নাম")
            if st.session_state.app_mode == "Farmer":
                u_id = st.text_input("NID Number")
            else:
                c1, c2, c3 = st.columns(3)
                dist = c1.selectbox("জেলা", BD_DISTRICTS)
                ser = c2.selectbox("সিরিজ", SERIES_LIST)
                num = c3.text_input("নাম্বার (১২-৩৪৫৬)")
                u_id = f"{dist}-{ser}-{num}".upper()
            
            if st.form_submit_button("নিবন্ধন সম্পন্ন করুন"):
                if u_name and u_id:
                    try:
                        supabase.table("riders").insert({"name": u_name, "rider_id": u_id, "category": st.session_state.app_mode}).execute()
                        registration_success(u_id)
                    except: st.error("এই আইডিটি ইতিমধ্যে সিস্টেমে আছে।")
