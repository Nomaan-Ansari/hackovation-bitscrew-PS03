import streamlit as st
import pandas as pd
import os
import shutil
import time
from io import BytesIO
from groq import Groq  # USING GROQ FOR VOICE TOO
from streamlit_mic_recorder import mic_recorder
from dotenv import load_dotenv # Ensure env vars are loaded
from src.database_manager import get_conn
import src.viz_engine as viz
from src.processor import process_scanned_document
from src.bot_engine import ask_financial_bot 

# Load environment variables (for GROQ_API_KEY)
load_dotenv()

st.set_page_config(page_title="AI Micro-ERP Intelligence", layout="wide")

# --- INITIALIZE SESSION STATE ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "show_chat" not in st.session_state:
    st.session_state.show_chat = False

# --- CSS / Styling Helper ---
def get_status_style(val):
    if val == 'Incomplete': return 'color: #ff4b4b; font-weight: bold' 
    if val == 'Partial': return 'color: #ffa500; font-weight: bold'    
    if val == 'Completed': return 'color: #00ff00; font-weight: bold'  
    return ''

# --- DIRECTORY SETUP ---
UPLOAD_DIR = "data/input"
ARCHIVE_DIR = "data/input_archive"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# --- NEW HELPER: GROQ WHISPER VOICE RECOGNITION ---
def recognize_audio(audio_bytes):
    """
    Sends audio bytes directly to Groq's Whisper API.
    No local FFmpeg or conversion required.
    """
    try:
        client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        
        # Wrap the bytes in a file-like object
        # We name it 'audio.webm' because streamlit-mic-recorder usually outputs WebM
        audio_file = BytesIO(audio_bytes)
        audio_file.name = "audio.webm" 
        
        transcription = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-large-v3", # Best model for Multilingual/Hinglish
            response_format="text",
            language="en" # Optional: You can remove this to let it auto-detect Hindi/English mixed
        )
        return transcription
        
    except Exception as e:
        return f"Voice Error: {e}"

# --- SIDEBAR: SYSTEM CONTROLS ---
st.sidebar.header("🛠️ System Controls")
st.session_state.show_chat = st.sidebar.toggle("💬 Enable AI Assistant", value=st.session_state.show_chat)

if st.sidebar.button("🗑️ Clear Cache"):
    st.cache_data.clear()
    st.session_state.chat_history = [] 
    st.sidebar.warning("Cache & Chat cleared.")

# --- LAYOUT MANAGEMENT ---
if st.session_state.show_chat:
    col_dashboard, col_chat = st.columns([3, 1]) 
else:
    col_dashboard = st.container() 
    col_chat = None

# =========================================================
#  SECTION 1: THE DASHBOARD (Inside col_dashboard)
# =========================================================
with col_dashboard:
    st.title("🛡️ AI Financial Intelligence Engine")
    
    tabs = st.tabs(["📤 Scan & Upload", "📑 Invoices", "🧾 Receipts", "🪣 Item Buckets", "📉 Merit Analysis", "📊 Analytics"])
    tab_scan, tab_inv, tab_rec, tab_buckets, tab_merit, tab_charts = tabs
    
    conn = get_conn()

    # --- TAB 1: SCAN ---
    with tab_scan:
        st.subheader("AI Document Scanner")
        uploaded_files = st.file_uploader("Drag & Drop Documents", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
        
        if uploaded_files and st.button("🚀 Process Files"):
            progress = st.progress(0)
            status = st.empty()
            for i, f in enumerate(uploaded_files):
                path = os.path.join(UPLOAD_DIR, f.name)
                with open(path, "wb") as buffer: buffer.write(f.getbuffer())
                
                with st.spinner(f"Analyzing {f.name}..."):
                    try:
                        process_scanned_document(path)
                        shutil.move(path, os.path.join(ARCHIVE_DIR, f.name))
                        st.success(f"✅ Saved: {f.name}")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                
                time.sleep(1) 
                progress.progress((i+1)/len(uploaded_files))
            st.rerun()

    # --- TAB 2: INVOICES ---
    with tab_inv:
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Invoices Received**")
            st.dataframe(pd.read_sql_query("SELECT id, date, total, status FROM inv_rec", conn).style.map(get_status_style, subset=['status']), use_container_width=True)
        with c2:
            st.write("**Invoices Sent**")
            st.dataframe(pd.read_sql_query("SELECT id, date, total, status FROM inv_sent", conn).style.map(get_status_style, subset=['status']), use_container_width=True)

    # --- TAB 3: RECEIPTS ---
    with tab_rec:
        c3, c4 = st.columns(2)
        with c3:
            st.write("**Receipts Received**")
            st.dataframe(pd.read_sql_query("SELECT id, inv_id, date, amount, status FROM rec_rec", conn).style.map(get_status_style, subset=['status']), use_container_width=True)
        with c4:
            st.write("**Receipts Sent**")
            st.dataframe(pd.read_sql_query("SELECT id, inv_id, date, amount, status FROM rec_sent", conn).style.map(get_status_style, subset=['status']), use_container_width=True)

    # --- TAB 4: BUCKETS ---
    with tab_buckets:
        bucket = st.selectbox("Select Tracker:", ["payment_to_be_received_inv", "payment_received_rec", "payment_to_be_sent_inv", "payment_to_be_done_rec"])
        st.dataframe(pd.read_sql_query(f"SELECT parent_id, item_name, qty_total, qty_fulfilled, status FROM {bucket}", conn).style.map(get_status_style, subset=['status']), use_container_width=True)

    # --- TAB 5: MERIT ---
    with tab_merit:
        c_m1, c_m2 = st.columns([1, 2])
        with c_m1:
            st.write("**Master Scores**")
            st.table(pd.read_sql_query("SELECT name, merit, streak FROM entity_master", conn))
        with c_m2:
            st.write("**Audit Trail**")
            st.dataframe(pd.read_sql_query("SELECT e.name, t.change, t.reason, t.timestamp FROM merit_audit_trail t JOIN entity_master e ON t.entity_id = e.id ORDER BY t.timestamp DESC", conn), use_container_width=True)

    # --- TAB 6: ANALYTICS ---
    with tab_charts:
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            f_chart = viz.get_fulfillment_chart()
            if f_chart: st.plotly_chart(f_chart, use_container_width=True)
            else: st.info("No data.")
        with c_g2:
            d_chart = viz.get_debt_exposure_chart()
            if d_chart: st.plotly_chart(d_chart, use_container_width=True)
            else: st.info("No debt.")
        
        m_chart = viz.get_merit_trend_chart()
        if m_chart: st.plotly_chart(m_chart, use_container_width=True)

    conn.close()

# =========================================================
#  SECTION 2: THE CHATBOT WITH VOICE (Inside col_chat)
# =========================================================
if col_chat:
    with col_chat:
        st.subheader("💬 Assistant")
        
        # 1. VOICE INPUT WIDGET
        # Note: streamlit-mic-recorder sends "WebM" format by default
        audio = mic_recorder(start_prompt="🎤 Speak", stop_prompt="⏹️ Stop", key='recorder')
        
        voice_text = None
        if audio:
            with st.spinner("Transcribing..."):
                voice_text = recognize_audio(audio['bytes'])
        
        # 2. CHAT HISTORY DISPLAY
        chat_container = st.container(height=500)
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # 3. INPUT HANDLING
        prompt = st.chat_input("Type or use 🎤 above...")
        
        if voice_text and not prompt:
            prompt = voice_text
            st.info(f"🗣️ Heard: {prompt}")

        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(prompt)

            with chat_container:
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        response = ask_financial_bot(prompt, st.session_state.chat_history)
                        st.markdown(response)
            
            st.session_state.chat_history.append({"role": "assistant", "content": response})