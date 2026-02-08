import streamlit as st
import pandas as pd
import os
import shutil
import time
from datetime import datetime
from src.database_manager import get_conn
import src.viz_engine as viz
from src.processor import process_scanned_document

st.set_page_config(page_title="AI Micro-ERP Intelligence", layout="wide")

# --- CSS / Styling Helper ---
def get_status_style(val):
    if val == 'Incomplete': return 'color: #ff4b4b; font-weight: bold' # Red
    if val == 'Partial': return 'color: #ffa500; font-weight: bold'    # Orange
    if val == 'Completed': return 'color: #00ff00; font-weight: bold'  # Green
    return ''

# --- DIRECTORY SETUP ---
# We still need these for temporary storage during processing
UPLOAD_DIR = "data/input"
ARCHIVE_DIR = "data/input_archive"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

# --- SIDEBAR ---
st.sidebar.header("🛠️ System Controls")
if st.sidebar.button("🗑️ Clear Cache"):
    st.cache_data.clear()
    st.sidebar.warning("Cache cleared.")

# --- MAIN INTERFACE ---
st.title("🛡️ AI Financial Intelligence Engine")
st.markdown("---")

# UPDATED TABS: Added "Scan & Upload" as the first tab
tabs = st.tabs(["📤 Scan & Upload", "📑 Invoices", "🧾 Receipts", "🪣 Item Buckets", "📉 Merit Analysis", "📊 Analytics"])
tab_scan, tab_inv, tab_rec, tab_buckets, tab_merit, tab_charts = tabs

conn = get_conn()

# --- TAB 1: SCAN & UPLOAD (New Drag-and-Drop Logic) ---
with tab_scan:
    st.subheader("AI Document Scanner")
    st.write("Drag and drop Invoices or Receipts here to process them instantly.")
    
    # File Uploader Widget
    uploaded_files = st.file_uploader("Upload Documents", type=['png', 'jpg', 'jpeg', 'pdf'], accept_multiple_files=True)
    
    if uploaded_files:
        if st.button("🚀 Process Uploaded Files"):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, uploaded_file in enumerate(uploaded_files):
                # 1. Save the uploaded file temporarily to disk
                temp_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                status_text.text(f"Analyzing: {uploaded_file.name}...")
                
                try:
                    # 2. Run the AI Processor
                    process_scanned_document(temp_path)
                    
                    # 3. Archive the file
                    archive_path = os.path.join(ARCHIVE_DIR, uploaded_file.name)
                    shutil.move(temp_path, archive_path)
                    
                    st.success(f"✅ Successfully processed and archived: {uploaded_file.name}")
                    
                except Exception as e:
                    st.error(f"❌ Error processing {uploaded_file.name}: {e}")
                
                # 4. Rate Limit Safety (5s pause)
                time.sleep(5)
                progress_bar.progress((i + 1) / len(uploaded_files))
            
            status_text.text("All files processed!")
            st.rerun()

# --- TAB 2: INVOICES ---
with tab_inv:
    st.subheader("Invoice Ledger (Requests for Payment)")
    c1, c2 = st.columns(2)
    with c1:
        st.write("**Invoices Received (To Vendors)**")
        df_inv_rec = pd.read_sql_query("SELECT id, date, total, status FROM inv_rec", conn)
        st.dataframe(df_inv_rec.style.map(get_status_style, subset=['status']), use_container_width=True)
    with c2:
        st.write("**Invoices Sent (To Clients)**")
        df_inv_sent = pd.read_sql_query("SELECT id, date, total, status FROM inv_sent", conn)
        st.dataframe(df_inv_sent.style.map(get_status_style, subset=['status']), use_container_width=True)

# --- TAB 3: RECEIPTS ---
with tab_rec:
    st.subheader("Receipt Ledger (Proof of Payment)")
    c3, c4 = st.columns(2)
    with c3:
        st.write("**Receipts Received (We Paid)**")
        df_rec_rec = pd.read_sql_query("SELECT id, inv_id, date, amount, status FROM rec_rec", conn)
        st.dataframe(df_rec_rec.style.map(get_status_style, subset=['status']), use_container_width=True)
    with c4:
        st.write("**Receipts Sent (They Paid)**")
        df_rec_sent = pd.read_sql_query("SELECT id, inv_id, date, amount, status FROM rec_sent", conn)
        st.dataframe(df_rec_sent.style.map(get_status_style, subset=['status']), use_container_width=True)

# --- TAB 4: ITEM BUCKETS ---
with tab_buckets:
    st.subheader("📦 Inventory-Linked Debt Reconciliation")
    bucket = st.selectbox("Select Tracker:", [
        "payment_to_be_received_inv", "payment_received_rec",
        "payment_to_be_sent_inv", "payment_to_be_done_rec"
    ])
    query = f"SELECT parent_id, item_name, qty_total, qty_fulfilled, status FROM {bucket}"
    df_b = pd.read_sql_query(query, conn)
    st.dataframe(df_b.style.map(get_status_style, subset=['status']), use_container_width=True)

# --- TAB 5: MERIT ANALYSIS ---
with tab_merit:
    st.subheader("📊 Entity Reputation & Merit Trail")
    col_m1, col_m2 = st.columns([1, 2])
    with col_m1:
        st.write("**Master Scores**")
        df_master = pd.read_sql_query("SELECT name, merit, streak FROM entity_master", conn)
        st.table(df_master)
    with col_m2:
        st.write("**Historical Audit Log**")
        trail_query = """
            SELECT e.name, t.change, t.reason, t.timestamp 
            FROM merit_audit_trail t 
            JOIN entity_master e ON t.entity_id = e.id 
            ORDER BY t.timestamp DESC
        """
        df_trail = pd.read_sql_query(trail_query, conn)
        st.dataframe(df_trail, use_container_width=True)

# --- TAB 6: ANALYTICS ---
with tab_charts:
    st.subheader("📈 Financial Performance Visuals")
    
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        f_chart = viz.get_fulfillment_chart()
        if f_chart: st.plotly_chart(f_chart, use_container_width=True)
        else: st.info("Fulfillment data unavailable.")
        
    with col_g2:
        d_chart = viz.get_debt_exposure_chart()
        if d_chart: st.plotly_chart(d_chart, use_container_width=True)
        else: st.info("No outstanding debt found.")
        
    st.markdown("---")
    m_chart = viz.get_merit_trend_chart()
    if m_chart: st.plotly_chart(m_chart, use_container_width=True)
    else: st.info("Insufficient merit history.")

conn.close()