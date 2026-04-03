import streamlit as st
from supabase import create_client, Client
import pandas as pd
from datetime import datetime, timedelta
import qrcode
import io

# --- 1. CONFIGURATION & SECRETS ---
st.set_page_config(page_title="FuelGuard Pro", page_icon="⛽", layout="wide")

# Supabase Connection
try:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(url, key)
except Exception as e:
    st.error("Secrets configuration missing! Please add SUPABASE_URL and SUPABASE_KEY.")
    st.stop()

LOCKOUT_HOURS = 72
APP_URL = "https://fuel-tracker.streamlit.app"

# --- 2. USAGE GUIDE POP-UP ---
@st.dialog("ব্যবহার নির্দেশিকা (How to Use)")
def show_instructions():
    st.markdown("""
    ### ⛽ ফুয়েলগার্ড (FuelGuard) এ স্বাগতম
    
    **প্রধান নিয়মাবলী:**
    1. **৭২ ঘণ্টার নিয়ম:** একবার তেল নেওয়ার পর পরবর্তী **৭২ ঘণ্টা** ওই আইডি লক থাকবে।
    2. **ছবি ভেরিফিকেশন:** তেল দেওয়ার সময় গাড়ির ছবি তোলা **বাধ্যতামূলক**।
    3. **সিস্টেম আপডেট:** ডাটা সরাসরি ক্লাউড ডাটাবেজে (Supabase) সেভ হয়, তাই যেকোনো পাম্প থেকে এটি চেক করা সম্ভব।

    **কিভাবে ব্যবহার করবেন:**
    - রাইডারের আইডি ইনপুট দিন বা QR স্ক্যান করুন।
    - সবুজ সংকেত দেখলে লিটার ইনপুট দিয়ে ছবি তুলুন।
    - **'Confirm & Save'** বাটনে ক্লিক করে কাজ শেষ করুন।
    """)
    if st.button("বুঝেছি, শুরু করি"):
        st.session_state.initialized = True
        st.rerun()

if "initialized" not in st.session_state:
    show_instructions()

# --- 3. DATABASE FUNCTIONS ---
def get_rider_data(rider_id):
    """ডাটাবেজ থেকে নির্দিষ্ট রাইডারের তথ্য আনে।"""
    clean_id = str(rider_id).strip().upper()
    response = supabase.table("riders").select("*").eq("rider_id", clean_id).execute()
    return response.data

def save_transaction(rider_id, liters, photo_file):
    """ছবি আপলোড করে এবং রাইডারের লাস্ট রিফিল টাইম আপডেট করে।"""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    file_name = f"{rider_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    
    try:
        # A. ছবি আপলোড (Supabase Storage)
        supabase.storage.from_("fuel_photos").upload(file_name, photo_file.getvalue())
        
        # B. রাইডার টেবিল আপডেট
        supabase.table("riders").update({
            "last_refill": now_str,
            "liters": liters
        }).eq("rider_id", rider_id).execute()
        
        return True
    except Exception as e:
        st.error(f"Error saving data: {e}")
        return False

# --- 4. MAIN INTERFACE ---
st.title("⛽ FuelGuard Pro: স্মার্ট মনিটরিং")

# হ্যান্ডেল কিউআর স্ক্যান বা ইনপুট
query_params = st.query_params
scanned_id = query_params.get("rider", "")

if not scanned_id:
    scanned_id = st.text_input("🔍 রাইডার আইডি লিখুন", placeholder="যেমন: DHAKA-METRO-HA-11-0101")

if scanned_id:
    rider_list = get_rider_data(scanned_id)
    
    if not rider_list:
        st.warning(f"❌ আইডি '{scanned_id}' ডাটাবেজে পাওয়া যায়নি।")
    else:
        rider = rider_list[0]
        st.header(f"👤 রাইডার: {rider['name']} ({rider['rider_id']})")
        
        # এলিজিবিলিটি লজিক
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
                liters_input = st.number_input("লিটারের পরিমাণ", 1.0, 100.0, 5.0)
                confirm_btn = st.button("💾 Confirm & Save to Cloud")
            
            with col2:
                photo = st.camera_input("নিরাপত্তার জন্য গাড়ির ছবি তুলুন")
            
            if confirm_btn:
                if photo:
                    with st.spinner("ডাটাবেজে সেভ হচ্ছে..."):
                        if save_transaction(rider['rider_id'], liters_input, photo):
                            st.success("সফলভাবে সেভ হয়েছে!")
                            st.balloons()
                            st.rerun()
                else:
                    st.error("⚠️ ছবি তোলা বাধ্যতামূলক!")

# --- 5. SIDEBAR: REGISTRATION & QR ---
st.sidebar.title("⚙️ এডমিন প্যানেল")

with st.sidebar.expander("📝 নতুন রাইডার রেজিস্ট্রেশন"):
    with st.form("reg_form"):
        new_id = st.text_input("গাড়ির আইডি (Unique ID)")
        new_name = st.text_input("রাইডারের নাম")
        if st.form_submit_button("নিবন্ধন করুন"):
            if new_id and new_name:
                try:
                    supabase.table("riders").insert({
                        "rider_id": new_id.upper().strip(),
                        "name": new_name,
                        "last_refill": None,
                        "liters": 0
                    }).execute()
                    st.success("নিবন্ধন সফল!")
                except:
                    st.error("এই আইডিটি ইতিমধ্যে নিবন্ধিত!")
            else:
                st.warning("সবগুলো ঘর পূরণ করুন।")

with st.sidebar.expander("📥 কিউআর কোড তৈরি"):
    qr_input = st.text_input("আইডি দিন (QR-এর জন্য)")
    if st.button("QR তৈরি করুন"):
        if qr_input:
            qr_link = f"{APP_URL}?rider={qr_input.upper().replace(' ', '%20')}"
            img = qrcode.make(qr_link)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            st.image(buf.getvalue(), caption=f"QR for: {qr_input.upper()}")
        else:
            st.warning("আইডি লিখুন।")

# লাইভ রিপোর্ট (Sidebar)
st.sidebar.markdown("---")
st.sidebar.subheader("📊 আজকের লাইভ রিপোর্ট")
try:
    today = datetime.now().strftime("%Y-%m-%d")
    # আজকের ট্রানজ্যাকশন ফিল্টার করা (সিম্পল লজিক)
    res = supabase.table("riders").select("liters").like("last_refill", f"{today}%").execute()
    count = len(res.data)
    total_l = sum(item['liters'] for item in res.data)
    st.sidebar.metric("আজকের রিফিল", f"{count} বার")
    st.sidebar.metric("মোট লিটার", f"{total_l} L")
except:
    pass
