import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import qrcode
import io

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

# Supabase কানেকশন চেক
if "SUPABASE_URL" in st.secrets and "SUPABASE_KEY" in st.secrets:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
else:
    st.error("Secrets configuration missing! Please add SUPABASE_URL and SUPABASE_KEY in Streamlit Settings.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app"

# --- 2. USAGE GUIDE POP-UP ---
@st.dialog("ব্যবহার নির্দেশিকা (How to Use)")
def show_instructions():
    st.markdown("""
    ### ⛽ ফুয়েলগার্ড (FuelGuard) এ স্বাগতম
    1. **৭২ ঘণ্টার নিয়ম:** একবার তেল নেওয়ার পর পরবর্তী **৭২ ঘণ্টা** ওই আইডি লক থাকবে।
    2. **ছবি ভেরিফিকেশন:** তেল দেওয়ার সময় গাড়ির ছবি তোলা বাধ্যতামূলক।
    3. **সিস্টেম আপডেট:** ডাটা সরাসরি ক্লাউড ডাটাবেজে সেভ হয়, তাই যেকোনো পাম্প থেকে আইডি চেক করা সম্ভব।
    """)
    if st.button("বুঝেছি, শুরু করি"):
        st.session_state.initialized = True
        st.rerun()

if "initialized" not in st.session_state:
    show_instructions()

# --- 3. DATABASE FUNCTIONS ---
def get_rider(rider_id):
    clean_id = str(rider_id).strip().upper()
    response = supabase.table("riders").select("*").eq("rider_id", clean_id).execute()
    return response.data

def update_refill(rider_id, liters, photo):
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_name = f"{rider_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    try:
        # A. ইমেজ আপলোড (Supabase Storage - Bucket name: fuel_photos)
        supabase.storage.from_("fuel_photos").upload(file_name, photo.getvalue())
        
        # B. রাইডার টেবিল আপডেট
        supabase.table("riders").update({
            "last_refill": now_str,
            "liters": liters
        }).eq("rider_id", rider_id).execute()
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False

# --- 4. MAIN INTERFACE ---
st.title("⛽ FuelGuard Pro: স্মার্ট মনিটরিং")

# হ্যান্ডেল কিউআর স্ক্যান বা ইনপুট
query_params = st.query_params
scanned_id = query_params.get("rider", "")

if not scanned_id:
    scanned_id = st.text_input("🔍 রাইডার আইডি লিখুন", placeholder="যেমন: PABNA-HA-11-0101")

if scanned_id:
    rider_list = get_rider(scanned_id)
    
    if not rider_list:
        st.warning(f"❌ আইডি '{scanned_id}' পাওয়া যায়নি।")
    else:
        rider = rider_list[0]
        st.header(f"👤 রাইডার: {rider['name']} ({rider['rider_id']})")
        
        eligible = True
        unlock_time = None
        if rider['last_refill']:
            last_dt = datetime.strptime(rider['last_refill'], "%Y-%m-%d %H:%M:%S")
            unlock_time = last_dt + timedelta(hours=LOCKOUT_HOURS)
            if datetime.now() < unlock_time:
                eligible = False

        if not eligible:
            st.error(f"### 🚫 রিফিল রিজেক্ট (Locked)")
            st.info(f"পরবর্তীতে তেল পাবেন: {unlock_time.strftime('%b %d, %I:%M %p')}")
        else:
            st.success("### ✅ রিফিল অনুমোদিত")
            col1, col2 = st.columns(2)
            with col1:
                liters_val = st.number_input("লিটার", 1.0, 100.0, 5.0)
                if st.button("💾 Confirm & Save"):
                    if "photo_taken" in st.session_state and st.session_state.photo_taken:
                        if update_refill(rider['rider_id'], liters_val, st.session_state.photo_taken):
                            st.success("সফলভাবে সেভ হয়েছে!")
                            st.balloons()
                            st.rerun()
                    else:
                        st.error("⚠️ ছবি তোলা বাধ্যতামূলক!")
            with col2:
                cam_photo = st.camera_input("গাড়ির ছবি")
                if cam_photo:
                    st.session_state.photo_taken = cam_photo

# --- 5. SIDEBAR: REGISTRATION & QR ---
st.sidebar.title("⚙️ এডমিন প্যানেল")

with st.sidebar.expander("📝 নতুন রাইডার নিবন্ধন"):
    with st.form("reg"):
        r_id = st.text_input("গাড়ির নাম্বার")
        r_name = st.text_input("নাম")
        if st.form_submit_button("নিবন্ধন"):
            if r_id and r_name:
                supabase.table("riders").insert({"rider_id": r_id.upper(), "name": r_name, "liters": 0}).execute()
                st.success("সফল!")
                st.rerun()

with st.sidebar.expander("📥 QR কোড"):
    qr_in = st.text_input("ID দিন")
    if st.button("QR তৈরি করুন"):
        link = f"{APP_URL}?rider={qr_in.upper()}"
        img = qrcode.make(link)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue())
