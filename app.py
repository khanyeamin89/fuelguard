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
#st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")
st.set_page_config(
    page_title="FuelGuard Pro | Smart Fuel Management System",
    page_icon="⛽",
    layout="wide",
    menu_items={
        'Get Help': 'vpersonal1123@gmail.com',
        'Report a bug': "vpersonal1123@gmail.com",
        'About': "# FuelGuard Pro\nAutomating fuel distribution with AI and QR technology for a more transparent future."
    }
)
st.title("⛽ FuelGuard Pro")

# Language Selection (Optional but good for UX)
lang = st.radio("Select Language / ভাষা নির্বাচন করুন", ["English", "বাংলা"], horizontal=True)

if lang == "English":
    st.markdown("""
        ### **Smart Fuel Management & Automated Distribution System**
        **FuelGuard Pro** is a cutting-edge AI solution designed to digitize and bring transparency to fuel distribution. 
        By leveraging Artificial Intelligence (AI) and QR technology, we ensure fair usage and prevent fraud.
        
        **Core Features:**
        * **AI Plate Recognition:** Instant vehicle identification via automated scanning.
        * **Secure QR Access:** Personal QR codes for fast and secure refueling.
        * **Smart Lockout:** Category-based refill limits to prevent fuel misuse.
        * **Real-time Monitoring:** PIN-protected dashboard for pump operators.
        ---
        *Save fuel, ensure transparency. Select your category below to get started.*
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        ### **স্মার্ট ফুয়েল ম্যানেজমেন্ট এবং অটোমেটেড ডিস্ট্রিবিউশন সিস্টেম**
        **FuelGuard Pro** বাংলাদেশে জ্বালানি বন্টন ব্যবস্থাকে ডিজিটাল এবং স্বচ্ছ করতে একটি আধুনিক AI সমাধান। 
        কৃত্রিম বুদ্ধিমত্তা (AI) এবং QR প্রযুক্তি ব্যবহারের মাধ্যমে আমরা জ্বালানি সাশ্রয় এবং সঠিক বন্টন নিশ্চিত করি।
        
        **মূল সুবিধাসমূহ:**
        * **AI Plate Recognition:** স্বয়ংক্রিয়ভাবে যানবাহনের নম্বর প্লেট শনাক্তকরণ।
        * **Secure QR Access:** দ্রুত এবং নিরাপদ জ্বালানি সংগ্রহের জন্য ব্যক্তিগত QR কোড।
        * **Smart Lockout:** জালিয়াতি রোধে রিফিল সময়সীমা স্বয়ংক্রিয় নিয়ন্ত্রণ।
        * **Real-time Monitoring:** পাম্প অপারেটরদের জন্য সুরক্ষিত ট্র্যাকিং সিস্টেম।
        ---
        *জ্বালানি সাশ্রয় করুন, স্বচ্ছতা নিশ্চিত করুন। শুরু করতে নিচে আপনার ক্যাটাগরি বেছে নিন।*
        """, unsafe_allow_html=True)
    
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

##if st.session_state.app_mode is None:
  ##  st.title("⛽ FuelGuard Pro")
    ## st.subheader("আপনার ক্যাটাগরি বেছে নিন")
    ## c1, c2 = st.columns(2)
    ## if c1.button("🚜 কৃষক (Farmer)"): st.session_state.app_mode = "Farmer"; st.rerun()
    ##  if c2.button("🚑 সরকারি (Govt)"): st.session_state.app_mode = "Govt"; st.rerun()
    ## if c1.button("🏍️ সাধারণ (General)"): st.session_state.app_mode = "General"; st.rerun()
    ## if c2.button("🏢 পাম্প অপারেটর", type="primary"): st.session_state.app_mode = "Pump"; st.rerun()
    ## st.stop()

# হোম স্ক্রিন UI
if st.session_state.app_mode is None:
    # মোবাইল এবং ডেস্কটপ উভয়ের জন্য অ্যাডভান্সড CSS
    st.markdown("""
        <style>
        /* বেসিক বাটন স্টাইল */
        div.stButton > button {
            height: 120px !important;
            font-size: 20px !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            margin-bottom: 10px !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            white-space: normal !important; /* লেখা ভেঙে নিচে আসবে */
            line-height: 1.2 !important;
        }

        /* মোবাইলের জন্য বিশেষ অ্যাডজাস্টমেন্ট */
        @media (max-width: 640px) {
            div.stButton > button {
                height: 100px !important;
                font-size: 18px !important;
                padding: 5px !important;
            }
            .stTitle {
                font-size: 28px !important;
            }
        }
        
        /* হোভার ইফেক্ট */
        div.stButton > button:hover {
            border: 2px solid #ff4b4b !important;
            color: #ff4b4b !important;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("⛽ FuelGuard Pro")
    st.subheader("আপনার ক্যাটাগরি বেছে নিন")
    st.write("---")

    # মোবাইলে বাটনগুলো যাতে একটার নিচে একটা আসে তাই কলাম গ্যাপ কমানো হয়েছে
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🚜 কৃষক\n(Farmer)", use_container_width=True): 
            st.session_state.app_mode = "Farmer"; st.rerun()
        if st.button("🏍️ সাধারণ\n(General)", use_container_width=True): 
            st.session_state.app_mode = "General"; st.rerun()

    with col2:
        if st.button("🚑 সরকারি\n(Govt)", use_container_width=True): 
            st.session_state.app_mode = "Govt"; st.rerun()
        if st.button("🏢 পাম্প\nঅপারেটর", type="primary", use_container_width=True): 
            st.session_state.app_mode = "Pump"; st.rerun()
    
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
    if st.sidebar.button("⬅️ Home"): 
        st.session_state.operator_auth = False
        st.session_state.app_mode = None
        st.rerun()

    # --- ১. পিন ভেরিফিকেশন (Security) ---
    if "operator_auth" not in st.session_state:
        st.session_state.operator_auth = False

    if not st.session_state.operator_auth:
        st.title("🔒 অপারেটর লগইন")
        base_pin = st.secrets.get("BASE_PIN", "1234")
        # প্রতিদিনের তারিখ অনুযায়ী ডায়নামিক পিন
        daily_pin = f"{base_pin}{datetime.now().strftime('%d')}"
        
        entered_pin = st.text_input("সিকিউরিটি পিন দিন", type="password")
        if st.button("লগইন", type="primary"):
            if entered_pin == daily_pin:
                st.session_state.operator_auth = True
                st.success("লগইন সফল!")
                st.rerun()
            else:
                st.error("ভুল পিন! দয়া করে সঠিক পিন দিন।")
        st.stop()

    # --- ২. লগইন সফল হলে অপারেটর ইন্টারফেস ---
    st.title("🏢 পাম্প অপারেটর ড্যাশবোর্ড")
    
    # ইনপুট মেথড সিলেকশন (এখন ৩টি অপশন)
    input_method = st.radio("ডাটা এন্ট্রি পদ্ধতি:", 
                            ["QR স্ক্যান করুন", "প্লেট স্ক্যান (AI)", "ম্যানুয়াল টাইপ"], 
                            horizontal=True)
    
    p_id = ""
    
    if input_method == "QR স্ক্যান করুন":
        st.write("রাইডারের QR কোডটি ক্যামেরার সামনে ধরুন:")
        scanned_data = qrcode_scanner(key='pump_qr_scanner')
        if scanned_data:
            p_id = scanned_data
            st.success(f"QR শনাক্ত হয়েছে: {p_id}")
            
    elif input_method == "প্লেট স্ক্যান (AI)":
        st.write("গাড়ির নাম্বার প্লেটের স্পষ্ট ছবি তুলুন:")
        plate_img = st.camera_input("ক্যামেরা ওপেন করুন", key="pump_plate_scanner")
        if plate_img:
            with st.spinner("AI প্লেট নম্বর রিড করছে..."):
                extracted_id, raw_txt = process_ai_image(plate_img)
                st.info(f"শনাক্তকৃত টেক্সট: {raw_txt}")
                p_id = extracted_id
    
    else:
        p_id = st.text_input("আইডি বা প্লেট নম্বর লিখুন")

    # ডাটাবেজ থেকে ইউজার চেক ও রিফিল ফর্ম
    if p_id:
        user = get_user_by_id(p_id)
        if user:
            st.info(f"**রাইডারের নাম:** {user['name']} | **ক্যাটাগরি:** {user['category']}")
            
            # রিফিল ইনপুট ফর্ম
            with st.container(border=True):
                col_f, col_l = st.columns(2)
                f_type = col_f.selectbox("জ্বালানির ধরণ", ["Octane", "Diesel", "Petrol"])
                liters = col_l.number_input("লিটারের পরিমাণ", 1.0, 100.0, 5.0)
                
                if st.button("রিফিল রেকর্ড সেভ করুন", type="primary", use_container_width=True):
                    confirm_refill_popup({
                        "id": user['rider_id'], 
                        "name": user['name'], 
                        "liters": liters, 
                        "type": f_type
                    })
        else:
            st.error("ডাটাবেজে কোনো রেকর্ড পাওয়া যায়নি। প্লেট স্ক্যান ভুল হলে ম্যানুয়ালি ট্রাই করুন।")

    if st.sidebar.button("🚪 লগআউট"):
        st.session_state.operator_auth = False
        st.rerun()
st.markdown("---")
st.caption("FuelGuard Pro 2026 | বাংলাদেশের মানুষের জন্য")
