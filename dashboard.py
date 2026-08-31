
"""
Video Analysis Analytics Dashboard — v3
Run: streamlit run dashboard_v3.py -- --output-dir path/to/output/folder
"""

import streamlit as st
import json
import re
import sys
import os
import tempfile
import time
import requests
from pathlib import Path
from fpdf import FPDF
import io
from collections import Counter
import pandas as pd

st.set_page_config(
    page_title="Video Analysis Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.sidebar.empty()


# ─────────────────────────── CSS ───────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap');
.section-header {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 0.85rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: #64748B;
    border-bottom: 1px solid #E2E8F0;
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
}
[data-testid="stSidebar"] {
    background-color: #F8FAFC !important;
    border-right: 1px solid #E2E8F0 !important;
}
[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 800 !important;
    color: #0F172A !important;
    letter-spacing: -0.02em !important;
    margin-bottom: 1rem !important;
}
[data-testid="stSidebar"] .stMarkdown h4 {
    font-family: 'Inter', sans-serif !important;
    font-weight: 700 !important;
    font-size: 0.75rem !important;
    color: #475569 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-top: 1.5rem !important;
    margin-bottom: 0.75rem !important;
}
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
    font-family: 'Inter', sans-serif !important;
}

[data-testid="baseButton-primary"] {
    background-color: #0F172A !important;
    color: #FFFFFF !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 0.5rem 1rem !important;
    border: none !important;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
}
[data-testid="baseButton-primary"]:hover {
    background-color: #1E293B !important;
}
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    border-radius: 8px !important;
    border-color: #CBD5E1 !important;
    background-color: #FFFFFF !important;
}
.kpi-badge {
    display: inline-block;
    padding: 3px 9px;
    border-radius: 20px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    margin: 2px 3px;
}
.badge-betting  { background:#FEF3C7; color:#92400E; border:1px solid #FDE68A; }
.badge-banking  { background:#E0F2FE; color:#0C4A6E; border:1px solid #BAE6FD; }
.badge-crypto   { background:#EDE9FE; color:#4C1D95; border:1px solid #DDD6FE; }
.badge-success  { background:#D1FAE5; color:#064E3B; border:1px solid #A7F3D0; }
.badge-fail     { background:#FEE2E2; color:#7F1D1D; border:1px solid #FECACA; }
.badge-qr       { background:#FFF7ED; color:#7C2D12; border:1px solid #FED7AA; }
.badge-neutral  { background:#F1F5F9; color:#475569; border:1px solid #E2E8F0; }
.verdict-row {
    display: flex; align-items: center; gap: 12px; padding: 9px 14px;
    border-radius: 8px; margin: 3px 0;
    border: 1px solid #E2E8F0; background: #FFFFFF;
    font-family: 'JetBrains Mono', monospace; font-size: 0.74rem;
}
.seg-num  { min-width:36px; color:#64748B; font-weight:700; }
.seg-time { min-width:145px; color:#0891B2; }
.seg-verdict { flex:1; color:#475569; }
.tx-alert, .qr-alert {
    border-radius:10px; padding:13px 17px; margin:7px 0;
    font-family:'JetBrains Mono',monospace; font-size:0.77rem;
}
.tx-alert { background:#FFF5F5; border:1px solid #FECACA; border-left:4px solid #DC2626; color:#475569; }
.tx-alert-title { color:#DC2626; font-weight:700; font-size:0.83rem; margin-bottom:5px; }
.qr-alert { background:#FFFBEB; border:1px solid #FDE68A; border-left:4px solid #D97706; color:#475569; }
.qr-alert-title { color:#D97706; font-weight:700; font-size:0.83rem; margin-bottom:5px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────── ECHARTS HELPER ────────────────────────
def echarts(option_js: str, height: int = 380, key: str = "chart"):
    html = f"""
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
    <div id="{key}" style="width:100%;height:{height}px;"></div>
    <script>
    (function(){{
        var dom = document.getElementById('{key}');
        var chart = echarts.init(dom, null, {{renderer:'svg'}});
        var option = {option_js};
        chart.setOption(option);
        window.addEventListener('resize', function(){{ chart.resize(); }});
    }})();
    </script>
    """
    st.components.v1.html(html, height=height + 10, scrolling=False)

ECHARTS_BASE = """
    backgroundColor: 'transparent',
    textStyle: {{ fontFamily: 'Inter, sans-serif', color: '#64748B' }},
"""

# ─────────────────────────── HELPERS ───────────────────────────────
def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def load_text(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def seg_label(seg):
    """Single unambiguous label from actual field values."""
    if seg.get("transaction_failed"):                   return "Failed Transaction"
    if (seg.get("transaction_executed") or 0) > 0:     return "Transaction Executed"
    if seg.get("qr_detected"):                          return "QR / Payment Flow"
    if (seg.get("transaction_likely") or 0) >= 70:     return "High Tx Likelihood"
    if (seg.get("banking_context") or 0) >= 40:        return "Banking Context"
    if (seg.get("crypto_context") or 0) >= 40:         return "Crypto Context"
    if (seg.get("transaction_likely") or 0) >= 30:     return "Possible Transaction"
    return "No Meaningful Activity"

def create_pdf_report(seg, img_path):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=16, style="B")
    pdf.cell(190, 10, txt=f"Segment {seg['segment_index']} Evidence Report", ln=True, align='C')
    
    pdf.set_font("helvetica", size=10)
    pdf.cell(190, 8, txt=f"Time: {seg['start_time']:.2f}s to {seg['end_time']:.2f}s", ln=True, align='C')
    pdf.ln(5)
    
    # Add Image
    if img_path and os.path.exists(img_path):
        # Resize/fit to page width
        pdf.image(img_path, x=10, y=30, w=190)
        # Shift cursor below the image
        pdf.set_y(150)
    else:
        pdf.cell(190, 10, txt="[No Image Available]", ln=True, align='C')
        pdf.ln(10)
        
    pdf.set_font("helvetica", size=12, style="B")
    pdf.cell(190, 10, txt="Classification Metrics", ln=True)
    pdf.set_font("helvetica", size=10)
    
    bank = seg.get("banking_context", 0) or 0
    cryp = seg.get("crypto_context", 0) or 0
    txlk = seg.get("transaction_likely", 0) or 0
    txex = seg.get("transaction_executed", 0) or 0
    
    pdf.cell(95, 8, txt=f"Banking Context: {bank}%", ln=False)
    pdf.cell(95, 8, txt=f"Crypto Context: {cryp}%", ln=True)
    pdf.cell(95, 8, txt=f"Transaction Likely: {txlk}%", ln=False)
    pdf.cell(95, 8, txt=f"Transaction Executed: {txex}%", ln=True)
    pdf.ln(10)
    
    pdf.set_font("helvetica", size=12, style="B")
    pdf.cell(190, 10, txt="Extracted Raw OCR Text", ln=True)
    pdf.set_font("helvetica", size=9)
    # Ensure latin-1 compatibility for FPDF default fonts
    ocr_text = seg.get("ocr_text", "No text detected.")
    safe_ocr = str(ocr_text).encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 5, txt=safe_ocr)
    
    return bytes(pdf.output())

def create_master_pdf_report(verdicts):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Title Page
    pdf.add_page()
    pdf.set_font("helvetica", size=24, style="B")
    pdf.cell(190, 40, txt="Master Evidence Report", ln=True, align='C')
    pdf.set_font("helvetica", size=14)
    pdf.cell(190, 10, txt=f"Total Segments Analyzed: {len(verdicts)}", ln=True, align='C')
    
    for seg in verdicts:
        pdf.add_page()
        pdf.set_font("helvetica", size=16, style="B")
        pdf.cell(190, 10, txt=f"Segment {seg['segment_index']} Evidence Report", ln=True, align='C')
        
        pdf.set_font("helvetica", size=10)
        pdf.cell(190, 8, txt=f"Time: {seg['start_time']:.2f}s to {seg['end_time']:.2f}s", ln=True, align='C')
        pdf.ln(5)
        
        # Add Image
        img_path = seg.get("proof_frame")
        if img_path and os.path.exists(img_path):
            pdf.image(img_path, x=10, y=30, w=190)
            pdf.set_y(150)
        else:
            pdf.cell(190, 10, txt="[No Image Available]", ln=True, align='C')
            pdf.ln(10)
            
        pdf.set_font("helvetica", size=12, style="B")
        pdf.cell(190, 10, txt="Classification Metrics", ln=True)
        pdf.set_font("helvetica", size=10)
        
        bank = seg.get("banking_context", 0) or 0
        cryp = seg.get("crypto_context", 0) or 0
        txlk = seg.get("transaction_likely", 0) or 0
        txex = seg.get("transaction_executed", 0) or 0
        
        pdf.cell(95, 8, txt=f"Banking Context: {bank}%", ln=False)
        pdf.cell(95, 8, txt=f"Crypto Context: {cryp}%", ln=True)
        pdf.cell(95, 8, txt=f"Transaction Likely: {txlk}%", ln=False)
        pdf.cell(95, 8, txt=f"Transaction Executed: {txex}%", ln=True)
        pdf.ln(10)
        
        pdf.set_font("helvetica", size=12, style="B")
        pdf.cell(190, 10, txt="Extracted Raw OCR Text", ln=True)
        pdf.set_font("helvetica", size=9)
        ocr_text = seg.get("ocr_text", "No text detected.")
        safe_ocr = str(ocr_text).encode("latin-1", "replace").decode("latin-1")
        pdf.multi_cell(0, 5, txt=safe_ocr)
        
    return bytes(pdf.output())

CATEGORIZED_KEYWORDS = {
    "Financial": [
        "deposit", "withdraw", "withdrawal", "wallet", "cashier", 
        "balance", "transfer", "payout", "topup", "add money", 
        "bank", "upi", "upi id", "gateway", "currency", "inr", "usd", 
        "crypto", "usdt", "usdc", "bitcoin", "btc", "ethereum", "eth", "tron", "bnb",
        "transaction", "my transactions", "recharge", "imps", "neft", "rtgs", "ecs", "ach",
        "gpay", "google pay", "phonepe", "phone pe", "paytm", "pay tm", "amazon pay", "bhim",
        "razorpay", "cashfree", "payu", "ccavenue", "billdesk", "rupay", "visa", "mastercard",
        "available balance", "winning balance", "deposit balance", "bonus balance",
        "beneficiary", "account number", "reference number", "transaction id",
        "qr", "qr code", "scan & pay", "scan qr"
    ],
    "Gaming": [
        "casino", "slot", "slots", "roulette", "blackjack", "poker", 
        "baccarat", "sports", "live sports", "fantasy", "betting", 
        "odds", "match", "tournament", "jackpot", "table games", 
        "crash game", "aviator", "mines", "spin"
    ],
    "Rewards": [
        "bonus", "referral", "rewards", "cashback", "spin", "wheel", 
        "promo", "promotion", "free bet", "vip", "welcome bonus", 
        "deposit bonus", "loyalty", "points", "claim"
    ],
    "Authentication": [
        "login", "sign in", "signin", "register", "sign up", "signup", 
        "kyc", "verify", "verification", "otp", "password", "account", 
        "forgot password", "join now", "register now", "phone number", "phone", "mobile", "mobile number", "email", "e-mail"
    ],
    "Legal": [
        "terms", "privacy", "policy", "license", "terms of service", 
        "responsible gaming", "18+", "anti-money laundering", "aml", 
        "disclaimer", "curacao", "malta", "isom"
    ],
    "Social": [
        "telegram", "whatsapp", "discord", "instagram", "facebook", 
        "twitter", "support", "contact us", "live chat", "channel"
    ]
}

def get_detected_categories(ocr_text):
    if not ocr_text:
        return {}
    text_lower = ocr_text.lower()
    detected = {}
    for cat, keywords in CATEGORIZED_KEYWORDS.items():
        found = [kw for kw in keywords if kw in text_lower]
        if found:
            detected[cat] = found
    return detected

def seg_color(seg):
    lbl = seg_label(seg)
    return {
        "Failed Transaction":    "#DC2626",
        "Transaction Executed":  "#059669",
        "QR / Payment Flow":     "#D97706",
        "High Tx Likelihood":    "#EF4444",
        "Banking Context":       "#0891B2",
        "Crypto Context":        "#7C3AED",
        "Possible Transaction":  "#F97316",
        "No Meaningful Activity":"#CBD5E1",
    }.get(lbl, "#94A3B8")

# ─────────────────────────── OUTPUT DIR ────────────────────────────
def get_output_dir():
    args = sys.argv
    if "--output-dir" in args:
        idx = args.index("--output-dir")
        if idx + 1 < len(args):
            return args[idx + 1]
    return None

cli_dir = get_output_dir()

with st.sidebar:
    st.markdown("""
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:24px; margin-top:-10px;">
            <div style="background:#0F172A; width:38px; height:38px; display:flex; align-items:center; justify-content:center; border-radius:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <span style="font-size:18px;">🎬</span>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center;">
                <span style="font-family:Inter,sans-serif; font-size:17px; font-weight:800; color:#0F172A; line-height:1.2; letter-spacing:-0.03em;">Video Analysis</span>
                <span style="font-family:Inter,sans-serif; font-size:11px; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; line-height:1.2; margin-top:2px;">Dashboard</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📁 Upload Video", "🌐 Crawl URL"])
    
    with tab1:
        uploaded_file = st.file_uploader("Select Video to Analyze", type=["mp4", "mov", "avi", "webm"])
        if uploaded_file is not None:
            if st.button("Start Analysis", type="primary", use_container_width=True, key="btn_upload"):
                with st.status("Analyzing Video...", expanded=True) as status:
                    st.write("Uploading and starting analysis...")
                    progress_bar = st.progress(0.0, text="Processing: 0%")
                    
                    try:
                        start_time = time.time()
                        
                        # Upload to API
                        files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                        resp = requests.post("http://127.0.0.1:8000/analyze", files=files)
                        resp.raise_for_status()
                        task_id = resp.json()["task_id"]
                        
                        st.write("Extracting frames and identifying signals...")
                        
                        # Poll for status
                        while True:
                            status_resp = requests.get(f"http://127.0.0.1:8000/status/{task_id}")
                            if status_resp.status_code == 200:
                                data = status_resp.json()
                                progress = data.get("progress", 0.0)
                                progress_bar.progress(progress, text=f"Processing: {int(progress * 100)}%")
                                
                                if data.get("status") == "complete":
                                    break
                                elif data.get("status") == "error":
                                    raise Exception(data.get("error_message", "Unknown error in backend"))
                            
                            time.sleep(1.0)
                        
                        elapsed = time.time() - start_time
                        st.session_state.output_dir = task_id  # Use task_id as the analysis identifier
                        
                        status.update(label="Analysis Complete!", state="complete", expanded=False)
                        st.rerun()
                    except Exception as e:
                        import traceback
                        err_msg = traceback.format_exc()
                        status.update(label="Analysis Failed", state="error", expanded=True)
                        st.error(f"Error during analysis: {e}\n\n{err_msg}")

    with tab2:
        if "active_crawl_task" not in st.session_state:
            crawl_url = st.text_input("Target Website URL", placeholder="https://example-betting.com")
            crawl_duration = st.slider("Crawl Duration (seconds)", min_value=10, max_value=120, value=30)
            
            if crawl_url:
                if st.button("Start Autonomous Crawl", type="primary", use_container_width=True, key="btn_crawl"):
                    try:
                        payload = {"url": crawl_url, "duration": crawl_duration}
                        resp = requests.post("http://127.0.0.1:8000/crawl", json=payload)
                        resp.raise_for_status()
                        task_id = resp.json()["task_id"]
                        st.session_state.active_crawl_task = task_id
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error starting crawl: {e}")
        else:
            task_id = st.session_state.active_crawl_task
            st.markdown(f"**Active Task ID:** `{task_id}`")
            
            try:
                status_resp = requests.get(f"http://127.0.0.1:8000/status/{task_id}")
                if status_resp.status_code == 200:
                    data = status_resp.json()
                    status = data.get("status")
                    crawler_state = data.get("crawler_state")
                    progress = data.get("progress", 0.0)
                    
                    if status == "error":
                        st.error(f"Error during crawl/analysis: {data.get('error_message')}")
                        if st.button("Clear & Restart", type="secondary"):
                            del st.session_state.active_crawl_task
                            st.rerun()
                    elif status == "complete":
                        st.success("Crawl & Analysis Complete!")
                        st.session_state.output_dir = str(task_id)
                        del st.session_state.active_crawl_task
                        
                        if st.button("View Report", type="primary"):
                            st.rerun()
                    else:
                        if crawler_state == "waiting_for_otp":
                            st.warning("⚠️ **Crawler Paused: OTP / Captcha Required!**")
                            with st.form("otp_form"):
                                otp_val = st.text_input("Enter the OTP sent to the registered mobile/email")
                                submitted = st.form_submit_button("Submit OTP")
                                if submitted:
                                    if otp_val:
                                        requests.post(f"http://127.0.0.1:8000/submit_otp/{task_id}", json={"otp": otp_val})
                                        st.success("OTP Submitted! Resuming...")
                                        time.sleep(1)
                                        st.rerun()
                                    else:
                                        st.error("Please enter a valid OTP.")
                        else:
                            st.info("🤖 **Bot is navigating the site and recording evidence...**")
                            progress_bar = st.progress(progress, text=f"Processing: {int(progress * 100)}%")
                            
                            # Polling logic via rerun
                            time.sleep(2)
                            st.rerun()
                else:
                    st.error("Failed to connect to backend API.")
                    if st.button("Clear"):
                        del st.session_state.active_crawl_task
                        st.rerun()
            except Exception as e:
                st.error(f"Error checking status: {e}")
                if st.button("Clear"):
                    del st.session_state.active_crawl_task
                    st.rerun()

    st.markdown("<hr style='margin:1.5rem 0; border-color:#E2E8F0;'>", unsafe_allow_html=True)
    st.markdown("#### Select Existing Analysis")
    
    # Check existing outputs via API
    try:
        analyses_resp = requests.get("http://127.0.0.1:8000/analyses_detailed")
        if analyses_resp.status_code == 200:
            detailed = analyses_resp.json()
            # Filter to only show complete tasks
            existing_outputs = [d for d in detailed if d.get("status") == "complete" or d.get("status") == "completed"]
        else:
            existing_outputs = []
    except Exception:
        existing_outputs = []
    
    if "output_dir" not in st.session_state:
        st.session_state.output_dir = cli_dir or (existing_outputs[0]["id"] if existing_outputs else "")
        
    options = [d["id"] for d in existing_outputs]
    if cli_dir and cli_dir not in options:
        options.append(cli_dir)

    def format_task(task_id):
        for d in existing_outputs:
            if d["id"] == task_id:
                return d["video_name"]
        return task_id

    selected_output = st.selectbox(
        "Previous Analyses", 
        options=options,
        index=0 if options else None,
        format_func=format_task,
        label_visibility="collapsed"
    )
    
    if selected_output and selected_output != st.session_state.output_dir:
        st.session_state.output_dir = selected_output
        st.rerun()

output_dir = st.session_state.get("output_dir", "")
if not output_dir:
    st.markdown("""
    <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 60vh; text-align: center; animation: fadeIn 0.5s ease-in-out;">
        <style>
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.95); }
            to { opacity: 1; transform: scale(1); }
        }
        </style>
        <div style="background: var(--secondary-background-color); border: 1px solid var(--secondary-background-color); border-radius: 50%; width: 96px; height: 96px; display: flex; align-items: center; justify-content: center; margin-bottom: 24px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);">
            <span style="font-size: 40px; opacity: 0.8;">🎬</span>
        </div>
        <h2 style="font-family: Inter, sans-serif; font-weight: 800; color: var(--text-color); margin-bottom: 12px; font-size: 28px; letter-spacing: -0.5px;">No Analysis Selected</h2>
        <p style="font-family: Inter, sans-serif; color: var(--text-color); opacity: 0.7; max-width: 450px; line-height: 1.6; font-size: 15px;">
            Upload a new video from the sidebar or input a URL to launch the autonomous bot. Your forensic dashboard will automatically generate upon completion.
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

output_path = Path(output_dir)

# ─────────────────────────── LOAD DATA ─────────────────────────────
summary_data = {}
try:
    summary_resp = requests.get(f"http://127.0.0.1:8000/analyses/{output_dir}/summary")
    if summary_resp.status_code == 200:
        summary_data = summary_resp.json()
except Exception:
    pass

verdicts   = summary_data.get("segment_verdicts", [])
bet_scores = summary_data.get("betting_segment_scores", [])
bet_tx     = summary_data.get("betting_transaction_attribution", [])
crypto_tx  = summary_data.get("crypto_betting_attribution", [])
summary    = summary_data.get("final_summary_txt", "")
report     = summary_data.get("final_verdict_report_txt", "")
metadata   = summary_data.get("metadata", {})
original_filename = summary_data.get("original_filename", "Unknown Video")

frames_dir_url = f"http://127.0.0.1:8000/outputs/{output_dir}/frames"

if not verdicts:
    st.error(f"No `segment_verdicts.json` found for `{output_dir}` from API. Check the analysis.")
    st.stop()

# ─────────────────────────── DERIVED STATS — real field math only ──
segment_count   = len(verdicts)
total_duration  = verdicts[-1]["end_time"] if verdicts else 0

# All computed from actual numeric fields — no assumed labels
qr_segments     = [v for v in verdicts if v.get("qr_detected")]
banking_segs    = [v for v in verdicts if (v.get("banking_context") or 0) > 30]
crypto_segs     = [v for v in verdicts if (v.get("crypto_context")  or 0) > 30]
tx_likely_segs  = [v for v in verdicts if (v.get("transaction_likely") or 0) >= 50]
tx_exec_segs    = [v for v in verdicts if (v.get("transaction_executed") or 0) > 0]
tx_failed_segs  = [v for v in verdicts if v.get("transaction_failed")]

# Transaction attempts detected
n_tx_att = len(bet_tx)

# Successful transactions detected
n_tx_exec = len([
    v for v in verdicts
    if v.get("transaction_executed", 0) > 0
])

# Infer failed attempts
if n_tx_att > 0 and n_tx_exec == 0:
    failed_tx_records = bet_tx

    failed_tx_times = [
        t["transaction_time"]
        for t in bet_tx
    ]
else:
    failed_tx_records = []
    failed_tx_times = []

betting_nonzero = [s for s in bet_scores if s > 0]
betting_pct     = round(len(betting_nonzero) / len(bet_scores) * 100, 1) if bet_scores else 0
max_bet_score   = max(bet_scores) if bet_scores else 0
avg_bet_score   = round(sum(betting_nonzero) / len(betting_nonzero), 1) if betting_nonzero else 0

# Extract Keyword Evidence
banking_hits = metadata.get("aggregated_banking_hits", [])
crypto_hits = metadata.get("aggregated_crypto_hits", [])

betting_evidence = metadata.get("betting_evidence", [])
betting_hits_set = set()
if betting_evidence:
    for ev in betting_evidence:
        if not ev or "suppressed" in ev: continue
        for key in ["brands", "betting_phrases", "wallet_phrases", "fantasy_ui", "casino", "sportsbook_ui", "promo"]:
            for hit in ev.get(key, []):
                betting_hits_set.add(str(hit))
betting_hits = sorted(list(betting_hits_set))

# ─────────────────────────── HEADER ────────────────────────────────
st.markdown(f"""
<div style='display:flex;align-items:baseline;gap:14px;margin-bottom:4px;'>
  <span style='font-family:Inter,sans-serif;font-weight:800;font-size:1.8rem;color:#1E293B;'>
    Video Analysis
  </span>
  <span style='font-family:JetBrains Mono,monospace;font-size:0.7rem;
  color:#0891B2;background:#E0F2FE;padding:4px 12px;border-radius:20px;
  border:1px solid #BAE6FD;font-weight:600;'>
    {output_dir}
  </span>
</div>
<div style='color:#64748B;font-family:JetBrains Mono,monospace;font-size:0.7rem;margin-bottom:26px;'>
  <span style='color:#1E293B;font-weight:700;'>{original_filename}</span><span>:Videoname</span> · {segment_count} segments · {total_duration:.1f}s total · {len(qr_segments)} QR detections · {len(failed_tx_times)} failed transactions
</div>
""", unsafe_allow_html=True)

# ─────────────────────────── TABS ──────────────────────────────────
tabs = st.tabs([
    "📊 Overview",
    "⏱ Timeline",
    "📈 Betting Analysis",
    "💳 Transactions",
    "🔍 Segment Explorer",
    "📋 Reports",
])


# ═══════════════════════════ TAB 1: OVERVIEW ═══════════════════════
with tabs[0]:

    # ── KPI Row with custom HTML cards ──
    metrics_html = f"""
    <style>
    .metric-grid {{
        display: grid; 
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); 
        gap: 16px; 
        margin-bottom: 24px; 
        font-family: Inter, sans-serif;
    }}
    .metric-card {{
        background: var(--background-color); 
        border: 1px solid var(--secondary-background-color); 
        border-radius: 12px; 
        padding: 16px; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        color: var(--text-color);
    }}
    .metric-card-dark {{
        background: var(--text-color); 
        border: 1px solid var(--text-color); 
        border-radius: 12px; 
        padding: 16px; 
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        color: var(--background-color);
    }}
    .metric-header {{
        display: flex; 
        justify-content: space-between; 
        align-items: center; 
        margin-bottom: 8px;
        font-size: 12px; 
        font-weight: 600; 
        text-transform: uppercase; 
        letter-spacing: 0.5px;
        opacity: 0.8;
    }}
    .metric-value {{
        font-family: 'JetBrains Mono', monospace; 
        font-size: 28px; 
        font-weight: 700; 
    }}
    .metric-sub {{
        font-size: 11px; 
        font-weight: 500; 
        margin-top: 4px;
        opacity: 0.7;
    }}
    </style>
    <div class="metric-grid">
        <div class="metric-card">
            <div class="metric-header">
                <span>Segments</span>
                <span>▶</span>
            </div>
            <div class="metric-value">{segment_count}</div>
            <div class="metric-sub">{total_duration:.1f}s video</div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <span>QR Detected</span>
                <span>⬛</span>
            </div>
            <div class="metric-value">{len(qr_segments)}</div>
            <div class="metric-sub">{len(qr_segments)} events</div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <span>Banking Segs</span>
                <span>🏦</span>
            </div>
            <div class="metric-value">{len(banking_segs)}</div>
            <div class="metric-sub">{(len(banking_segs)/segment_count*100) if segment_count else 0:.0f}% coverage</div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <span>Crypto Segs</span>
                <span>₿</span>
            </div>
            <div class="metric-value">{len(crypto_segs)}</div>
            <div class="metric-sub">{(len(crypto_segs)/segment_count*100) if segment_count else 0:.0f}% coverage</div>
        </div>
        <div class="metric-card">
            <div class="metric-header">
                <span>Betting Cov</span>
                <span>🎯</span>
            </div>
            <div class="metric-value">{betting_pct}%</div>
            <div class="metric-sub">{len(betting_nonzero)} segments</div>
        </div>
        <div class="{'metric-card-dark' if failed_tx_times else 'metric-card'}">
            <div class="metric-header">
                <span>Failed Tx</span>
                <span>🛑</span>
            </div>
            <div class="metric-value">{len(failed_tx_times)}</div>
            <div class="metric-sub">unconfirmed attempts</div>
        </div>
    </div>
    """
    st.markdown(metrics_html, unsafe_allow_html=True)

    col_a, col_b = st.columns([1, 1.2])

    with col_a:
        st.markdown('<div class="section-header" style="display:flex; align-items:center; gap:8px;"><span>🎯</span> Executive Summary</div>', unsafe_allow_html=True)
        
        exec_html = '<div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(130px, 1fr)); gap:12px; font-family:Inter,sans-serif;">'
        
        def exec_card(label, value):
            return (
                '<div style="background:var(--secondary-background-color); border:1px solid var(--secondary-background-color); border-radius:8px; padding:12px; display:flex; flex-direction:column; color:var(--text-color);">'
                f'<span style="font-size:11px; font-weight:600; opacity:0.7; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">{label}</span>'
                f'<span style="font-family:\'JetBrains Mono\',monospace; font-size:14px; font-weight:700;">{value}</span>'
                '</div>'
            )
            
        exec_html += exec_card("Betting Coverage", f"{betting_pct}%")
        exec_html += exec_card("Max Betting Score", f"{max_bet_score:.1f} / 100")
        exec_html += exec_card("Avg Betting Score", f"{avg_bet_score:.1f} / 100")
        exec_html += exec_card("Banking Segments", f"{len(banking_segs)} / {segment_count}")
        exec_html += exec_card("Crypto Segments", f"{len(crypto_segs)} / {segment_count}")
        exec_html += exec_card("QR / Payment", f"{len(qr_segments)} events")
        exec_html += exec_card("High Tx Likely", f"{len(tx_likely_segs)} segments")
        exec_html += exec_card("Failed Tx", f"{len(failed_tx_times)} attempts")
        exec_html += exec_card("Tx Executed", f"{len(tx_exec_segs)} confirmed")
        exec_html += exec_card("Video Duration", f"{total_duration:.1f}s")
        
        exec_html += '</div>'
        
        # Add keywords section
        if banking_hits or crypto_hits or betting_hits:
            exec_html += '<div style="margin-top:16px; background:var(--background-color); border:1px solid var(--secondary-background-color); border-radius:8px; padding:12px;">'
            exec_html += '<div style="font-size:12px; font-weight:600; opacity:0.8; margin-bottom:8px; color:var(--text-color);">DISCOVERED KEYWORD EVIDENCE</div>'
            exec_html += '<div style="display:flex; flex-wrap:wrap; gap:6px;">'
            
            def badge(word, color, bg):
                return f'<span style="background:{bg}; color:{color}; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700; font-family:\'JetBrains Mono\',monospace; border:1px solid {color}40;">{word}</span>'
                
            for word in banking_hits:
                exec_html += badge(word, "#0891B2", "#CFFAFE")
            for word in crypto_hits:
                exec_html += badge(word, "#7C3AED", "#EDE9FE")
            for word in betting_hits:
                exec_html += badge(word, "#D97706", "#FEF3C7")
                
            exec_html += '</div></div>'
            
        st.markdown(exec_html, unsafe_allow_html=True)

    with col_b:
        st.markdown('<div class="section-header" style="display:flex; align-items:center; gap:8px;"><span>🛡️</span> Signal Coverage</div>', unsafe_allow_html=True)
        
        sig_html = '<div style="background:var(--background-color); border:1px solid var(--secondary-background-color); border-radius:12px; padding:20px; box-shadow:0 1px 2px rgba(0,0,0,0.05); font-family:Inter,sans-serif; display:flex; flex-direction:column; gap:20px; color:var(--text-color);">'
        
        def sig_bar(label, count, total, color):
            pct = (count / total * 100) if total else 0
            return (
                '<div>'
                '<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">'
                f'<span style="font-size:14px; font-weight:600;">{label}</span>'
                '<div style="display:flex; align-items:center; gap:8px;">'
                f'<span style="font-size:12px; opacity:0.7;">{count} / {total}</span>'
                f'<span style="font-family:JetBrains Mono,monospace; font-size:12px; font-weight:700; background:var(--secondary-background-color); padding:2px 6px; border-radius:4px;">{pct:.1f}%</span>'
                '</div>'
                '</div>'
                '<div style="width:100%; height:10px; background:var(--secondary-background-color); border-radius:5px; overflow:hidden;">'
                f'<div style="width:{pct}%; height:100%; background:{color}; border-radius:5px;"></div>'
                '</div>'
                '</div>'
            )
            
        sig_html += sig_bar("Banking Context", len(banking_segs), segment_count, "#0891B2")
        sig_html += sig_bar("Crypto Context", len(crypto_segs), segment_count, "#7C3AED")
        sig_html += sig_bar("Transaction Likely", len(tx_likely_segs), segment_count, "#DC2626")
        sig_html += sig_bar("QR Code Detected", len(qr_segments), segment_count, "#D97706")
        sig_html += sig_bar("Betting Coverage", len(betting_nonzero), len(bet_scores) or 1, "#F59E0B")
        sig_html += sig_bar("Failed Tx", len(failed_tx_times), max(len(bet_tx),1), "#991B1B")
        
        sig_html += '</div>'
        st.markdown(sig_html, unsafe_allow_html=True)

    # ── Signal Area Chart ──
    st.markdown('<div class="section-header" style="display:flex; align-items:center; gap:8px;"><span>📈</span> Signal Strength Over Time</div>', unsafe_allow_html=True)
    st.markdown("""<div style='font-family:Inter,sans-serif;font-size:0.79rem;opacity:0.7;margin-bottom:12px;'>
    Continuous tracking of banking, crypto, and transaction intent across the video duration.
    </div>""", unsafe_allow_html=True)
    
    if verdicts:
        df = pd.DataFrame([{
            'Time (s)': v.get('start_time', 0),
            'Banking': v.get('banking_context', 0),
            'Crypto': v.get('crypto_context', 0),
            'Tx Likely': v.get('transaction_likely', 0)
        } for v in verdicts])
        df.set_index('Time (s)', inplace=True)
        st.area_chart(df, color=["#0891B2", "#7C3AED", "#DC2626"], use_container_width=True)

    # ── Timeline hero (full width) ──
    st.markdown('<div class="section-header">Video Event Timeline — Full Duration Overview</div>', unsafe_allow_html=True)
    st.markdown("""<div style='font-family:Inter,sans-serif;font-size:0.79rem;color:#64748B;margin-bottom:12px;'>
    Six signal lanes plotted across the full video. Hover each bar for exact timestamps and context scores.
    </div>""", unsafe_allow_html=True)

    def build_gantt(segs, lane_idx, color, name, extra_fields=None):
        """Build Gantt items with rich tooltip data from actual fields."""
        items = []
        for s in segs:
            bank  = s.get("banking_context",    0) if isinstance(s, dict) and "banking_context" in s else 0
            crypt = s.get("crypto_context",      0) if isinstance(s, dict) and "crypto_context"  in s else 0
            txl   = s.get("transaction_likely",  0) if isinstance(s, dict) and "transaction_likely" in s else 0
            st_   = s.get("start_time", 0)
            en_   = s.get("end_time",   0)
            dur   = round(en_ - st_, 2)
            tooltip = (f"{name}\\n"
                       f"Start: {st_:.2f}s | End: {en_:.2f}s | Duration: {dur}s\\n"
                       f"Banking: {bank:.1f}% | Crypto: {crypt:.1f}% | Tx Likely: {txl:.1f}%")
            items.append({
                "name":      name,
                "value":     [lane_idx, st_, en_, tooltip],
                "itemStyle": {"color": color}
            })
        return items

    betting_segs_obj = [verdicts[i] for i, sc in enumerate(bet_scores)
                        if i < len(verdicts) and sc > 0]
    high_tx_segs     = [v for v in verdicts if (v.get("transaction_likely") or 0) >= 50]

    failed_segs_obj = []
    for t in bet_tx:
        if not t.get("transaction_used_for_betting"):
            m = re.match(r"([\d.]+)[–\-]([\d.]+)", t.get("transaction_time", ""))
            if m:
                st2, en2 = float(m.group(1)), float(m.group(2))
                matched  = next((v for v in verdicts if abs(v["start_time"] - st2) < 1.0), None)
                failed_segs_obj.append(matched if matched else
                    {"start_time": st2, "end_time": en2, "banking_context": 0,
                     "crypto_context": 0, "transaction_likely": 0})

    lanes = [
        (betting_segs_obj, 5, "#D97706", "Betting UI"),
        (qr_segments,      4, "#F59E0B", "QR / Payment"),
        (high_tx_segs,     3, "#DC2626", "High Tx Likelihood"),
        (failed_segs_obj,  2, "#991B1B", "Failed Transaction"),
        (banking_segs,     1, "#0891B2", "Banking Context"),
        (crypto_segs,      0, "#7C3AED", "Crypto Context"),
    ]
    lane_names = ["Crypto Context", "Banking Context", "Failed Transaction",
                  "High Tx Likelihood", "QR / Payment", "Betting UI"]

    all_items = []
    for segs, idx, color, name in lanes:
        all_items.extend(build_gantt(segs, idx, color, name))

    gantt_js   = json.dumps(all_items)
    lanes_js   = json.dumps(lane_names)
    total_dur  = total_duration

    echarts(f"""{{
        backgroundColor: 'transparent',
        textStyle: {{ fontFamily: 'Inter', color: '#64748B' }},
        tooltip: {{
            trigger: 'item',
            formatter: function(p) {{
                var lines = p.value[3].split('\\n');
                var html = '<div style="font-family:JetBrains Mono,monospace;font-size:12px;line-height:1.8;">';
                html += '<b style="font-size:13px;color:#1E293B;">' + lines[0] + '</b><br/>';
                for(var i=1;i<lines.length;i++) html += lines[i] + '<br/>';
                html += '</div>';
                return html;
            }},
            backgroundColor:'#fff', borderColor:'#E2E8F0',
            padding:12, extraCssText:'box-shadow:0 2px 12px rgba(0,0,0,0.08);border-radius:8px;'
        }},
        grid: {{ left:150, right:20, top:10, bottom:38 }},
        xAxis: {{
            type:'value', min:0, max:{total_dur:.1f},
            axisLabel: {{ formatter: function(v){{return v+'s';}},
                fontFamily:'JetBrains Mono', fontSize:10, color:'#94A3B8' }},
            splitLine: {{ lineStyle:{{ color:'#F1F5F9' }} }},
            axisLine: {{ lineStyle:{{ color:'#E2E8F0' }} }}
        }},
        yAxis: {{
            data: {lanes_js},
            axisLabel: {{ fontFamily:'Inter', fontSize:11, color:'#475569', fontWeight:500 }},
            axisLine:{{ show:false }}, axisTick:{{ show:false }}, splitLine:{{ show:false }}
        }},
        series: [{{
            type:'custom',
            renderItem: function(params, api) {{
                var ci   = api.value(0);
                var s    = api.coord([api.value(1), ci]);
                var e    = api.coord([api.value(2), ci]);
                var h    = api.size([0,1])[1] * 0.52;
                var rect = echarts.graphic.clipRectByRect(
                    {{ x:s[0], y:s[1]-h/2, width:e[0]-s[0], height:h }},
                    {{ x:params.coordSys.x, y:params.coordSys.y,
                       width:params.coordSys.width, height:params.coordSys.height }}
                );
                return rect && {{
                    type:'rect', transition:['shape'],
                    shape:rect, style:api.style({{opacity:0.88}})
                }};
            }},
            itemStyle:{{ borderRadius:3 }},
            encode:{{ x:[1,2], y:0 }},
            data: {gantt_js}
        }}]
    }}""", height=310, key="gantt_overview")

    st.markdown("""<div style='display:flex;gap:18px;flex-wrap:wrap;font-family:Inter,sans-serif;
    font-size:0.71rem;margin-top:6px;color:#64748B;'>
      <span style='display:flex;align-items:center;gap:5px;'><span style='background:#D97706;width:11px;height:11px;border-radius:2px;display:inline-block;'></span>Betting UI</span>
      <span style='display:flex;align-items:center;gap:5px;'><span style='background:#F59E0B;width:11px;height:11px;border-radius:2px;display:inline-block;'></span>QR / Payment</span>
      <span style='display:flex;align-items:center;gap:5px;'><span style='background:#DC2626;width:11px;height:11px;border-radius:2px;display:inline-block;'></span>High Tx Likelihood</span>
      <span style='display:flex;align-items:center;gap:5px;'><span style='background:#991B1B;width:11px;height:11px;border-radius:2px;display:inline-block;'></span>Failed Transaction</span>
      <span style='display:flex;align-items:center;gap:5px;'><span style='background:#0891B2;width:11px;height:11px;border-radius:2px;display:inline-block;'></span>Banking Context</span>
      <span style='display:flex;align-items:center;gap:5px;'><span style='background:#7C3AED;width:11px;height:11px;border-radius:2px;display:inline-block;'></span>Crypto Context</span>
    </div>""", unsafe_allow_html=True)

    # ── Alert boxes ──
    st.markdown('<div class="section-header">Key Event Alerts</div>', unsafe_allow_html=True)
    alert_cols = st.columns(3)

    qr_times = [f"{v['start_time']:.2f}s–{v['end_time']:.2f}s" for v in qr_segments]
    with alert_cols[0]:
        if qr_times:
            times_html = "<br>".join(f"• {t}" for t in qr_times)
            st.markdown(f"""<div class='qr-alert'>
              <div class='qr-alert-title'>⬛ QR / Payment Codes Detected</div>
              {times_html}</div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='verdict-row' style='color:#94A3B8;'>No QR codes detected</div>", unsafe_allow_html=True)

    with alert_cols[1]:
        if tx_likely_segs:
            times_html = "<br>".join(f"• {v['start_time']:.2f}s–{v['end_time']:.2f}s" for v in tx_likely_segs[:6])
            st.markdown(f"""<div class='qr-alert'>
              <div class='qr-alert-title'>⚡ High-Confidence Transaction Segments</div>
              {times_html}</div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='verdict-row' style='color:#94A3B8;'>No high-confidence transactions</div>", unsafe_allow_html=True)

    with alert_cols[2]:
        if failed_tx_times:
            times_html = "<br>".join(f"• {t}" for t in failed_tx_times)
            st.markdown(f"""<div class='tx-alert'>
              <div class='tx-alert-title'>✗ Failed / Unconfirmed Transaction Attempts</div>
              {times_html}</div>""", unsafe_allow_html=True)
        else:
            st.markdown("<div class='verdict-row' style='color:#94A3B8;'>No failed transactions detected</div>", unsafe_allow_html=True)


# ═══════════════════════════ TAB 2: TIMELINE ═══════════════════════
with tabs[1]:
   
    # Sankey
    st.markdown('<div class="section-header">Sankey — Inference Story</div>', unsafe_allow_html=True)
    st.markdown("""<div style='font-family:Inter,sans-serif;font-size:0.79rem;color:#64748B;margin-bottom:14px;'>
    End-to-end narrative from raw content to transaction outcome. Node widths = segment counts from your data.
    </div>""", unsafe_allow_html=True)

    n_betting  = len(betting_segs_obj)
    n_banking  = len(banking_segs)
    n_qr       = len(qr_segments)
    n_tx_att   = len(bet_tx)
    n_tx_fail  = len(bet_tx)
    n_tx_succ  = len([t for t in bet_tx if t.get("transaction_used_for_betting")])
    n_no_act   = max(segment_count - n_betting, 1)
    n_qr_only  = max(n_qr - n_tx_fail, 0)

    sankey_nodes = json.dumps([
        {"name":"Video"},
        {"name":"Betting UI"},
        {"name":"No Betting Activity"},
        {"name":"Wallet / Banking"},
        {"name":"QR Payment Code"},
        {"name":"Transaction Attempt"},
        {"name":"Transaction Failed"},
        {"name":"QR — No Transaction"},
    ])
    sankey_links_data = []

    if n_betting > 0:
        sankey_links_data.append({
            "source":"Video",
            "target":"Betting UI",
            "value":n_betting
        })

    if n_no_act > 0:
        sankey_links_data.append({
            "source":"Video",
            "target":"No Betting Activity",
            "value":n_no_act
        })

    if n_banking > 0:
        sankey_links_data.append({
            "source":"Betting UI",
            "target":"Wallet / Banking",
            "value":n_banking
        })

    if n_qr > 0:
        sankey_links_data.append({
            "source":"Wallet / Banking",
            "target":"QR Payment Code",
            "value":n_qr
        })

    if n_tx_att > 0:
        sankey_links_data.append({
            "source":"QR Payment Code",
            "target":"Transaction Attempt",
            "value":n_tx_att
        })

    if n_tx_fail > 0:
        sankey_links_data.append({
            "source":"Transaction Attempt",
            "target":"Transaction Failed",
            "value":n_tx_fail
        })

    if n_qr_only > 0:
        sankey_links_data.append({
            "source":"QR Payment Code",
            "target":"QR — No Transaction",
            "value":n_qr_only
        })

    sankey_links = json.dumps(sankey_links_data)

    echarts(f"""{{
        backgroundColor:'transparent',
        textStyle:{{ fontFamily:'Inter', color:'#64748B' }},
        tooltip:{{
            trigger:'item', triggerOn:'mousemove',
            backgroundColor:'#fff', borderColor:'#E2E8F0',
            formatter: function(p){{
                return '<span style="font-family:Inter;font-weight:600;color:#1E293B;">'
                    + p.name + '</span><br/>'
                    + '<span style="font-family:JetBrains Mono;font-size:12px;color:#475569;">'
                    + (p.value||'') + ' segments</span>';
            }},
            padding:12, extraCssText:'box-shadow:0 2px 12px rgba(0,0,0,0.08);border-radius:8px;'
        }},
        series:[{{
            type:'sankey', layout:'none',
            emphasis:{{ focus:'adjacency' }},
            nodeAlign:'left', nodeGap:16, nodeWidth:24,
            left:'2%', right:'10%', top:'6%', bottom:'6%',
            data:{sankey_nodes},
            links:{sankey_links},
            lineStyle:{{ color:'source', opacity:0.22, curveness:0.5 }},
            itemStyle:{{ borderWidth:0 }},
            label:{{ fontFamily:'Inter', fontSize:12, fontWeight:600, color:'#1E293B' }},
            color:['#475569','#D97706','#CBD5E1','#0891B2','#F59E0B','#DC2626','#991B1B','#94A3B8']
        }}]
    }}""", height=330, key="sankey_tab2")
    st.markdown(
        '<div class="section-header">Chronological Event Feed</div>',
        unsafe_allow_html=True
    )
    st.markdown('<p style="font-size:12px; color:#64748B; margin-top:-10px; margin-bottom:20px;">A forensic step-by-step reconstruction of the video\'s activity timeline.</p>', unsafe_allow_html=True)
    
    events_html = '<div style="position:relative; padding-left:24px; border-left:2px solid #E2E8F0; margin-left:16px; font-family:Inter,sans-serif;">'
    
    for idx, seg in enumerate(verdicts):
        bScore = bet_scores[idx] if idx < len(bet_scores) else 0
        
        is_significant = False
        title = "Normal Activity"
        desc = "No major forensic signals detected."
        dot_color = "#E2E8F0"
        title_color = "#64748B"
        icon = "▶"
        
        if (seg.get("transaction_executed", 0) or 0) > 50:
            title = "Transaction Executed"
            desc = "A confirmed payment or transaction occurred on screen."
            dot_color = "#10B981"
            title_color = "#047857"
            icon = "✓"
            is_significant = True
        elif seg.get("qr_detected"):
            title = "QR / Payment Scan Detected"
            desc = "A QR code or explicit payment mechanism was found."
            dot_color = "#F59E0B"
            title_color = "#D97706"
            icon = "⬛"
            is_significant = True
        elif (seg.get("transaction_likely", 0) or 0) > 50:
            title = "High Transaction Likelihood"
            desc = f"Transaction context score is very high ({seg.get('transaction_likely')}%)"
            dot_color = "#EF4444"
            title_color = "#B91C1C"
            icon = "⚠"
            is_significant = True
        elif bScore > 50:
            title = "Betting UI Detected"
            desc = f"Betting application features found (Score: {bScore}%)"
            dot_color = "#F59E0B"
            title_color = "#B45309"
            icon = "⚠"
            is_significant = True
        elif (seg.get("banking_context", 0) or 0) > 40:
            title = "Wallet / Banking App Opened"
            desc = f"Financial application context detected (Score: {seg.get('banking_context')}%)"
            dot_color = "#06B6D4"
            title_color = "#0369A1"
            icon = "🏦"
            is_significant = True
        elif (seg.get("crypto_context", 0) or 0) > 40:
            title = "Crypto Application Context"
            desc = f"Cryptocurrency interface detected (Score: {seg.get('crypto_context')}%)"
            dot_color = "#A855F7"
            title_color = "#7E22CE"
            icon = "₿"
            is_significant = True
            
        start_t_str = f"{seg.get('start_time', 0):.1f}"
        failed_tx = next((tx for tx in bet_tx if tx.get('transaction_time', '') and start_t_str in tx.get('transaction_time', '')), None)
        
        if failed_tx and not failed_tx.get('transaction_used_for_betting'):
            title = "Failed Transaction Attempt"
            desc = "A transaction was initiated but did not complete successfully."
            dot_color = "#991B1B"
            title_color = "#7F1D1D"
            icon = "⚠"
            is_significant = True
            
        if is_significant or idx == 0 or idx == len(verdicts) - 1:
            if idx == 0 and not is_significant:
                title = "Video Analysis Started"
                desc = "Beginning chronological scan."
            if idx == len(verdicts) - 1 and not is_significant:
                title = "Analysis Complete"
                desc = "End of video feed."
                dot_color = "#94A3B8"
                title_color = "#475569"
                icon = "■"
                
            ocr_html = ""
            if seg.get("ocr_text"):
                safe_ocr = str(seg.get("ocr_text")).encode("latin-1", "replace").decode("latin-1")
                if len(safe_ocr) > 100: safe_ocr = safe_ocr[:100] + "..."
                ocr_html = f"<div style='margin-top:8px; background:#F8FAFC; border:1px solid #F1F5F9; padding:8px; border-radius:4px; font-family:JetBrains Mono,monospace; font-size:11px; color:#64748B;'><span style='font-weight:bold; color:#94A3B8; margin-right:8px;'>OCR:</span>{safe_ocr}</div>"
                
            events_html += f"""
            <div style="position:relative; margin-bottom:32px;">
                <div style="position:absolute; left:-37px; top:0; width:24px; height:24px; border-radius:50%; background:{dot_color}; border:4px solid #FFF; display:flex; align-items:center; justify-content:center; box-shadow:0 1px 2px rgba(0,0,0,0.1);"></div>
                <div style="background:#FFF; border:1px solid #E2E8F0; border-radius:8px; padding:16px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:8px;">
                        <div style="display:flex; align-items:center; gap:8px;">
                            <span style="color:{title_color}; font-size:14px;">{icon}</span>
                            <span style="color:{title_color}; font-weight:700; font-size:14px;">{title}</span>
                        </div>
                        <span style="background:#F8FAFC; padding:4px 8px; border-radius:4px; font-family:JetBrains Mono,monospace; font-size:11px; font-weight:700; color:#94A3B8;">{seg.get('start_time', 0):.1f}s - {seg.get('end_time', 0):.1f}s</span>
                    </div>
                    <div style="font-size:13px; color:#475569;">{desc}</div>
                    {ocr_html}
                </div>
            </div>
            """
            
    events_html += "</div>"
    st.markdown(events_html, unsafe_allow_html=True)


# ═══════════════════════════ TAB 3: BETTING ════════════════════════
with tabs[2]:
    if bet_scores:
        st.markdown('<div class="section-header">Betting Confidence Trend</div>', unsafe_allow_html=True)
        st.markdown("""<div style='font-family:Inter,sans-serif;font-size:0.79rem;color:#64748B;margin-bottom:12px;'>
        Smooth area chart — betting evidence signal strength across the full video. Values from <b>betting_segment_scores.json</b>.
        </div>""", unsafe_allow_html=True)

        seg_times = [round(verdicts[i]["start_time"], 2) if i < len(verdicts) else i
                     for i in range(len(bet_scores))]
        area_data = [[seg_times[i], bet_scores[i]] for i in range(len(bet_scores))]
        area_js   = json.dumps(area_data)

        echarts(f"""{{
            backgroundColor:'transparent',
            textStyle:{{ fontFamily:'Inter', color:'#64748B' }},
            tooltip:{{
                trigger:'axis',
                axisPointer:{{ type:'cross', label:{{ backgroundColor:'#D97706' }} }},
                backgroundColor:'#fff', borderColor:'#E2E8F0',
                formatter: function(params){{
                    var p = params[0];
                    return '<span style="font-family:JetBrains Mono;font-size:12px;">'
                        + 'Time: ' + p.value[0] + 's<br/>'
                        + 'Betting Score: <b style="color:#D97706;">' + p.value[1].toFixed(1) + '</b>'
                        + '</span>';
                }},
                padding:12, extraCssText:'box-shadow:0 2px 12px rgba(0,0,0,0.08);border-radius:8px;'
            }},
            grid:{{ left:52, right:20, top:24, bottom:50 }},
            xAxis:{{
                type:'value', name:'Time (seconds)',
                nameLocation:'middle', nameGap:30,
                nameTextStyle:{{ fontFamily:'Inter', fontSize:11, color:'#64748B' }},
                axisLabel:{{ formatter:'{{value}}s', fontFamily:'JetBrains Mono', fontSize:10, color:'#94A3B8' }},
                splitLine:{{ lineStyle:{{ color:'#F8FAFC' }} }},
                axisLine:{{ lineStyle:{{ color:'#E2E8F0' }} }}
            }},
            yAxis:{{
                type:'value', name:'Score', nameLocation:'middle', nameGap:36,
                nameTextStyle:{{ fontFamily:'Inter', fontSize:11, color:'#64748B' }},
                min:0, max:100,
                axisLabel:{{ fontFamily:'JetBrains Mono', fontSize:10, color:'#94A3B8' }},
                splitLine:{{ lineStyle:{{ color:'#F1F5F9' }} }}
            }},
            series:[{{
                type:'line', data:{area_js},
                smooth:true, symbol:'none',
                areaStyle:{{
                    color:{{type:'linear',x:0,y:0,x2:0,y2:1,
                        colorStops:[{{offset:0,color:'rgba(217,119,6,0.38)'}},
                                    {{offset:1,color:'rgba(217,119,6,0.02)'}}]}}
                }},
                lineStyle:{{ color:'#D97706', width:2.5 }},
                markLine:{{
                    silent:true,
                    data:[{{yAxis:50}}],
                    lineStyle:{{ color:'#CBD5E1', type:'dashed', width:1.5 }},
                    label:{{ formatter:'50% threshold', fontFamily:'Inter',
                            fontSize:10, color:'#94A3B8', position:'end' }}
                }}
            }}]
        }}""", height=290, key="area_betting")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Segments with Betting", len(betting_nonzero), f"{betting_pct}% of total")
        c2.metric("Coverage",              f"{betting_pct}%")
        c3.metric("Max Score",             f"{max_bet_score:.1f}")
        c4.metric("Avg Score (non-zero)",  f"{avg_bet_score:.1f}")

        # ── Video Activity Heatmap (replaces Context Evolution) ──
        st.markdown('<div class="section-header">Video Activity Heatmap</div>', unsafe_allow_html=True)
        st.markdown("""<div style='font-family:Inter,sans-serif;font-size:0.79rem;color:#64748B;margin-bottom:12px;'>
        Each row = one activity type. Colored bars show exactly <b>where</b> that activity occurs across the video.
        Hover for segment details, timestamps, and confidence values.
        </div>""", unsafe_allow_html=True)

        # Build 5-row heatmap: Betting, Banking, Crypto, QR/Payment, High Tx
        heatmap_lanes = [
            ("Betting UI",         "#D97706", [
                verdicts[i] for i, sc in enumerate(bet_scores)
                if i < len(verdicts) and sc > 50
            ]),
            ("Banking Context",    "#0891B2", [
                v for v in verdicts if (v.get("banking_context") or 0) > 30
            ]),
            ("Crypto Context",     "#7C3AED", [
                v for v in verdicts if (v.get("crypto_context") or 0) > 20
            ]),
            ("QR / Payment",       "#F59E0B", [
                v for v in verdicts if v.get("qr_detected")
            ]),
            ("High Tx Likelihood", "#DC2626", [
                v for v in verdicts if (v.get("transaction_likely") or 0) > 50
            ]),
        ]
        hm_items = []
        hm_lane_names = []
        for lane_i, (lane_name, lane_color, lane_segs) in enumerate(heatmap_lanes):
            hm_lane_names.append(lane_name)
            for seg in lane_segs:
                sc_bet  = bet_scores[seg["segment_index"]-1] if seg["segment_index"]-1 < len(bet_scores) else 0
                sc_bank = seg.get("banking_context", 0) or 0
                sc_cryp = seg.get("crypto_context", 0) or 0
                sc_txlk = seg.get("transaction_likely", 0) or 0
                dur     = round(seg["end_time"] - seg["start_time"], 2)
                tip     = (f"Seg #{seg['segment_index']} — {lane_name}\\n"
                           f"Start: {seg['start_time']:.2f}s | End: {seg['end_time']:.2f}s | Duration: {dur}s\\n"
                           f"Banking: {sc_bank:.1f}% | Crypto: {sc_cryp:.1f}% | Tx Likely: {sc_txlk:.1f}%\\n"
                           f"Betting Score: {sc_bet:.1f} | QR: {'Yes' if seg.get('qr_detected') else 'No'}")
                hm_items.append({
                    "value": [lane_i, seg["start_time"], seg["end_time"], tip],
                    "itemStyle": {"color": lane_color}
                })

        hm_items_js   = json.dumps(hm_items)
        hm_lanes_js   = json.dumps(hm_lane_names)

        echarts(f"""{{
            backgroundColor:'transparent',
            textStyle:{{ fontFamily:'Inter', color:'#64748B' }},
            tooltip:{{
                trigger:'item',
                formatter: function(p) {{
                    var lines = p.value[3].split('\\n');
                    var html = '<div style="font-family:JetBrains Mono,monospace;font-size:12px;line-height:1.9;">';
                    html += '<b style="font-size:13px;color:#1E293B;">' + lines[0] + '</b><br/>';
                    for(var i=1;i<lines.length;i++) html += lines[i] + '<br/>';
                    html += '</div>';
                    return html;
                }},
                backgroundColor:'#fff', borderColor:'#E2E8F0',
                padding:12, extraCssText:'box-shadow:0 2px 12px rgba(0,0,0,0.08);border-radius:8px;'
            }},
            grid:{{ left:145, right:20, top:10, bottom:38 }},
            xAxis:{{
                type:'value', min:0, max:{total_dur:.1f},
                name:'Time (seconds)', nameLocation:'middle', nameGap:26,
                nameTextStyle:{{ fontFamily:'Inter', fontSize:11, color:'#64748B' }},
                axisLabel:{{ formatter: function(v){{return v+'s';}},
                    fontFamily:'JetBrains Mono', fontSize:10, color:'#94A3B8' }},
                splitLine:{{ lineStyle:{{ color:'#F1F5F9' }} }},
                axisLine:{{ lineStyle:{{ color:'#E2E8F0' }} }}
            }},
            yAxis:{{
                type:'category', data:{hm_lanes_js},
                inverse:true,
                axisLabel:{{ fontFamily:'Inter', fontSize:11, color:'#475569', fontWeight:500 }},
                axisLine:{{ show:false }}, axisTick:{{ show:false }}, splitLine:{{ show:false }}
            }},
            series:[{{
                type:'custom',
                renderItem: function(params, api) {{
                    var ci = api.value(0);
                    var s  = api.coord([api.value(1), ci]);
                    var e  = api.coord([api.value(2), ci]);
                    var h  = api.size([0,1])[1] * 0.54;
                    var rect = echarts.graphic.clipRectByRect(
                        {{ x:s[0], y:s[1]-h/2, width:Math.max(e[0]-s[0],3), height:h }},
                        {{ x:params.coordSys.x, y:params.coordSys.y,
                           width:params.coordSys.width, height:params.coordSys.height }}
                    );
                    return rect && {{
                        type:'rect', transition:['shape'],
                        shape:rect, style:api.style({{opacity:0.88, borderRadius:3}})
                    }};
                }},
                encode:{{ x:[1,2], y:0 }},
                data:{hm_items_js}
            }}]
        }}""", height=290, key="activity_heatmap")

        # Betting runs
        st.markdown('<div class="section-header">Continuous Betting Runs</div>', unsafe_allow_html=True)

        runs = []
        run_start = None
        for i, s in enumerate(bet_scores):
            if s > 0 and run_start is None:
                run_start = i
            elif s == 0 and run_start is not None:
                runs.append((run_start + 1, i, i - run_start))
                run_start = None
        if run_start is not None:
            runs.append((run_start + 1, len(bet_scores), len(bet_scores) - run_start))

        for start, end, length in sorted(runs, key=lambda x: -x[2])[:10]:
            t_s = verdicts[start-1]["start_time"] if start-1 < len(verdicts) else 0
            t_e = verdicts[min(end-1, len(verdicts)-1)]["end_time"]
            st.markdown(f"""
            <div class='verdict-row'>
              <span class='seg-num'>#{start}–{end}</span>
              <span class='seg-time'>{t_s:.2f}s – {t_e:.2f}s</span>
              <span class='seg-verdict'>{length} consecutive betting segments</span>
              <span class='kpi-badge badge-betting'>{t_e-t_s:.1f}s duration</span>
            </div>""", unsafe_allow_html=True)

    if bet_tx:
        st.markdown('<div class="section-header">Betting Transaction Attribution</div>', unsafe_allow_html=True)
        for tx in bet_tx:
            ev         = tx.get("evidence", {})
            final_s    = ev.get("final_score", tx.get("betting_purpose_score", 0))
            brands     = ev.get("brands", [])
            conf       = tx.get("confidence", 0)
            attributed = tx.get("transaction_used_for_betting", False)
            suppressed = ev.get("suppressed", False)

            badge      = '<span class="kpi-badge badge-success">ATTRIBUTED</span>' if attributed else '<span class="kpi-badge badge-fail">NOT ATTRIBUTED</span>'
            supp       = '<span class="kpi-badge badge-neutral">SUPPRESSED</span>' if suppressed else ""
            brand_html = "".join(f'<span class="kpi-badge badge-crypto">{b}</span>' for b in brands)

            st.markdown(f"""
            <div class='verdict-row'>
              <span class='seg-num'>Seg {tx['segment_index']}</span>
              <span class='seg-time'>{tx['transaction_time']}</span>
              <span class='seg-verdict'>Score: {final_s:.1f} · Conf: {conf:.0f}% {brand_html}</span>
              {badge} {supp}
            </div>""", unsafe_allow_html=True)


# ═══════════════════════════ TAB 4: TRANSACTIONS ═══════════════════
with tabs[3]:
    st.markdown('<div class="section-header">Transaction Funnel</div>', unsafe_allow_html=True)
    st.markdown("""<div style='font-family:Inter,sans-serif;font-size:0.79rem;color:#64748B;margin-bottom:12px;'>
    Count-based pipeline: from all segments down to successful transactions.
    Shows exactly how many segments qualified at each detection stage.
    </div>""", unsafe_allow_html=True)

    # Funnel counts
    f_total   = len(verdicts)
    f_betting = len([i for i, sc in enumerate(bet_scores) if i < len(verdicts) and sc > 50])
    f_banking = len([v for v in verdicts if (v.get("banking_context") or 0) > 30])
    f_crypto  = len([v for v in verdicts if (v.get("crypto_context")  or 0) > 20])
    f_qr      = len([v for v in verdicts if v.get("qr_detected")])
    f_txhigh  = len([v for v in verdicts if (v.get("transaction_likely") or 0) > 50])
    f_txexec  = len([v for v in verdicts if (v.get("transaction_executed") or 0) > 50])

    funnel_data = [
        {"name": f"Total Segments",          "value": f_total,   "pct": 100.0},
        {"name": f"Betting Segments",        "value": f_betting, "pct": round(f_betting/f_total*100,1) if f_total else 0},
        {"name": f"Banking Segments",        "value": f_banking, "pct": round(f_banking/f_total*100,1) if f_total else 0},
        {"name": f"Crypto Segments",         "value": f_crypto,  "pct": round(f_crypto/f_total*100,1)  if f_total else 0},
        {"name": f"QR Events",               "value": f_qr,      "pct": round(f_qr/f_total*100,1)      if f_total else 0},
        {"name": f"High Tx Segments",        "value": f_txhigh,  "pct": round(f_txhigh/f_total*100,1)  if f_total else 0},
        {"name": f"Successful Transactions", "value": f_txexec,  "pct": round(f_txexec/f_total*100,1)  if f_total else 0},
    ]

    funnel_js = json.dumps([
        {
            "name":  d["name"],
            "value": d["value"],
            "label_text": f"{d['value']} ({d['pct']}%)",
        }
        for d in funnel_data
    ])
    funnel_colors = json.dumps([
        "#475569","#D97706","#0891B2","#7C3AED","#F59E0B","#DC2626","#059669"
    ])

    echarts(f"""{{
        backgroundColor:'transparent',
        textStyle:{{ fontFamily:'Inter', color:'#64748B' }},
        tooltip:{{
            trigger:'item',
            backgroundColor:'#fff', borderColor:'#E2E8F0',
            formatter: function(p) {{
                return '<div style="font-family:JetBrains Mono,monospace;font-size:12px;line-height:1.8;">'
                    + '<b style="font-size:13px;color:#1E293B;">' + p.name + '</b><br/>'
                    + 'Count: <b>' + p.value + '</b><br/>'
                    + 'Share of total: <b>' + (p.value/{f_total}*100).toFixed(1) + '%</b>'
                    + '</div>';
            }},
            padding:12, extraCssText:'box-shadow:0 2px 12px rgba(0,0,0,0.08);border-radius:8px;'
        }},
        color: {funnel_colors},
        series:[{{
            type:'funnel',
            left:'15%', right:'20%', top:20, bottom:10,
            width:'65%',
            min:0, max:{f_total},
            minSize:'4%', maxSize:'100%',
            sort:'none',
            gap:3,
            label:{{
                show:true, position:'right',
                fontFamily:'JetBrains Mono', fontSize:12, color:'#475569',
                formatter: function(p){{
                    return p.value + '  (' + (p.value/{f_total}*100).toFixed(1) + '%)';
                }}
            }},
            itemStyle:{{ borderWidth:0, opacity:0.9 }},
            emphasis:{{
                label:{{ fontWeight:'bold', color:'#1E293B' }},
                itemStyle:{{ opacity:1 }}
            }},
            data: {funnel_js}.map(function(d){{return {{name:d.name, value:d.value}};}}),
        }}]
    }}""", height=340, key="tx_funnel")

    st.markdown('<div class="section-header">QR / Payment Flow Events</div>', unsafe_allow_html=True)
    if qr_segments:
        for v in qr_segments:
            tx_conf   = v.get("transaction_likely",  0) or 0
            bank_conf = v.get("banking_context",     0) or 0
            cryp_conf = v.get("crypto_context",      0) or 0
            st.markdown(f"""
            <div class='verdict-row'>
              <span class='seg-num'>Seg {v['segment_index']}</span>
              <span class='seg-time'>{v['start_time']:.2f}s – {v['end_time']:.2f}s</span>
              <span class='seg-verdict'>Tx Likely: {tx_conf:.0f}% · Banking: {bank_conf:.0f}% · Crypto: {cryp_conf:.0f}%</span>
              <span class='kpi-badge badge-qr'>QR DETECTED</span>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div class='verdict-row' style='color:#94A3B8;'>No QR codes detected.</div>", unsafe_allow_html=True)

    st.markdown('<div class="section-header">Failed / Unconfirmed Transaction Attempts</div>', unsafe_allow_html=True)
    if failed_tx_records:
        for t in failed_tx_records:
            t_range   = t["transaction_time"]
            bps       = t.get("betting_purpose_score", 0)
            conf      = t.get("confidence", 0)
            ev        = t.get("evidence", {})
            raw_s     = ev.get("raw_score", "—")
            final_s   = ev.get("final_score", bps)
            m         = re.match(r"([\d.]+)[–\-]([\d.]+)", t_range)
            matched   = next((v for v in verdicts
                              if m and abs(v["start_time"] - float(m.group(1))) < 1.0), None)
            tx_conf   = matched.get("transaction_likely", 0) if matched else "—"
            st.markdown(f"""
            <div class='tx-alert'>
              <div class='tx-alert-title'>✗ {t_range} — Attempt Not Confirmed</div>
              Tx Likelihood: {tx_conf}% · Betting Score: {final_s:.1f} · Confidence: {conf:.0f}%
              · No execution confirmation · QR code present
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("<div class='verdict-row' style='color:#94A3B8;'>No failed transactions detected.</div>", unsafe_allow_html=True)


# ═══════════════════════════ TAB 5: SEGMENT EXPLORER ═══════════════
with tabs[4]:
    if "seg_idx_sel" not in st.session_state:
        st.session_state.seg_idx_sel = 0

    num_segments = len(verdicts)

    # Top Control Bar
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([1.5, 2, 1.5, 2.5])
    with ctrl_col1:
        if st.button("⬅️ Previous", use_container_width=True, disabled=(st.session_state.seg_idx_sel <= 0)):
            st.session_state.seg_idx_sel -= 1
            st.rerun()
    with ctrl_col2:
        seg_options = [f"Seg {v['segment_index']:03d} | {v['start_time']:.2f}s – {v['end_time']:.2f}s" for v in verdicts]
        selected_option = st.selectbox(
            "Select Segment", 
            seg_options, 
            index=st.session_state.seg_idx_sel,
            label_visibility="collapsed"
        )
        new_idx = int(selected_option.split("Seg ")[1].split(" ")[0]) - 1
        if new_idx != st.session_state.seg_idx_sel:
            st.session_state.seg_idx_sel = new_idx
            st.rerun()
    with ctrl_col3:
        if st.button("Next ➡️", use_container_width=True, disabled=(st.session_state.seg_idx_sel >= num_segments - 1)):
            st.session_state.seg_idx_sel += 1
            st.rerun()
    with ctrl_col4:
        try:
            m_pdf = create_master_pdf_report(verdicts)
            st.download_button(
                label="📥 Master PDF (All Segments)",
                data=m_pdf,
                file_name=f"master_report_{original_filename}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Master PDF Error: {e}")

    seg = verdicts[st.session_state.seg_idx_sel]

    st.markdown('<div class="section-header" style="margin-top:15px;">Segment Explorer</div>', unsafe_allow_html=True)
    col_left, col_right = st.columns([1, 1])

    with col_left:
        # Horizontal bar comparison (replaces radar)
        bank_val  = seg.get("banking_context",    0) or 0
        cryp_val  = seg.get("crypto_context",     0) or 0
        txlk_val  = seg.get("transaction_likely", 0) or 0
        txex_val  = seg.get("transaction_executed",0) or 0
        bet_val   = bet_scores[st.session_state.seg_idx_sel] if st.session_state.seg_idx_sel < len(bet_scores) else 0
        qr_val    = 100 if seg.get("qr_detected") else 0

        st.markdown(f"""
        <div style='background:#FAFAFA;border:1px solid #E2E8F0;border-radius:12px;
        padding:18px;margin-top:10px;'>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.62rem;
          color:#D97706;margin-bottom:14px;letter-spacing:0.1em;text-transform:uppercase;'>
            SEGMENT {seg['segment_index']} — REAL VALUES
          </div>
        """, unsafe_allow_html=True)

        def horiz_bar(label, value, color, max_val=100):
            pct = min(value / max_val * 100, 100) if max_val else 0
            st.markdown(f"""
            <div style='margin:9px 0;'>
              <div style='display:flex;justify-content:space-between;
              font-family:JetBrains Mono,monospace;font-size:0.76rem;margin-bottom:4px;'>
                <span style='color:#475569;'>{label}</span>
                <span style='color:{color};font-weight:700;'>{value:.1f}%</span>
              </div>
              <div style='background:#F1F5F9;border-radius:5px;height:9px;overflow:hidden;'>
                <div style='background:{color};height:100%;width:{pct:.1f}%;
                border-radius:5px;'></div>
              </div>
            </div>""", unsafe_allow_html=True)

        horiz_bar("Banking Context",    bank_val,  "#0891B2")
        horiz_bar("Crypto Context",     cryp_val,  "#7C3AED")
        horiz_bar("Transaction Likely", txlk_val,  "#DC2626")
        horiz_bar("Tx Executed",        txex_val,  "#059669")
        horiz_bar("Betting Score",      bet_val,   "#D97706")
        horiz_bar("QR Detected",        qr_val,    "#F59E0B")

        st.markdown("</div>", unsafe_allow_html=True)

        # Badges
        badges = []
        if seg.get("qr_detected"):                   badges.append('<span class="kpi-badge badge-qr">QR DETECTED</span>')
        if seg.get("transaction_failed"):             badges.append('<span class="kpi-badge badge-fail">TX FAILED</span>')
        if bank_val > 50:                             badges.append('<span class="kpi-badge badge-banking">BANKING</span>')
        if cryp_val > 50:                             badges.append('<span class="kpi-badge badge-crypto">CRYPTO</span>')
        if bet_val > 0:                               badges.append(f'<span class="kpi-badge badge-betting">BET {bet_val:.0f}</span>')
        if txlk_val >= 70:                            badges.append('<span class="kpi-badge badge-fail">HIGH TX</span>')
        if badges:
            st.markdown("<div style='margin-top:12px;'>" + "".join(badges) + "</div>", unsafe_allow_html=True)

    with col_right:
        lbl   = seg_label(seg)
        color = seg_color(seg)
        dur   = seg["end_time"] - seg["start_time"]

        st.markdown(f"""
        <div style='background:#FAFAFA;border:1px solid #E2E8F0;border-radius:12px;
        padding:20px;margin-bottom:16px;'>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.62rem;
          color:#64748B;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.08em;'>CLASSIFICATION</div>
          <div style='font-family:Inter,sans-serif;font-size:1.0rem;
          font-weight:700;color:{color};margin-bottom:10px;'>{lbl}</div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.72rem;color:#94A3B8;'>
            {seg['start_time']:.3f}s → {seg['end_time']:.3f}s &nbsp;·&nbsp; {dur:.2f}s duration
          </div>
          <div style='font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#94A3B8;margin-top:5px;'>
            QR Detected: <b style='color:#1E293B;'>{'Yes' if seg.get("qr_detected") else 'No'}</b>
            &nbsp;·&nbsp; Tx Failed: <b style='color:#1E293B;'>{'Yes' if seg.get("transaction_failed") else 'No'}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

        bar_cats   = ["Banking Context","Crypto Context","Tx Likely","Tx Executed","Betting Score","QR Signal"]
        bar_vals   = [bank_val, cryp_val, txlk_val, txex_val, bet_val, qr_val]
        bar_colors = ["#0891B2","#7C3AED","#DC2626","#059669","#D97706","#F59E0B"]
        bar_cats_js  = json.dumps(bar_cats)
        bar_vals_js  = json.dumps(bar_vals)
        bar_col_js   = json.dumps(bar_colors)

        echarts(f"""{{
            backgroundColor:'transparent',
            textStyle:{{ fontFamily:'Inter', color:'#64748B' }},
            tooltip:{{
                trigger:'axis', axisPointer:{{ type:'none' }},
                backgroundColor:'#fff', borderColor:'#E2E8F0',
                formatter: function(params){{
                    var p = params[0];
                    return '<span style="font-family:JetBrains Mono;font-size:12px;">'
                        + p.name + ': <b>' + p.value + '%</b></span>';
                }},
                padding:10, extraCssText:'box-shadow:0 2px 8px rgba(0,0,0,0.08);border-radius:8px;'
            }},
            grid:{{ left:120, right:50, top:10, bottom:10 }},
            xAxis:{{
                type:'value', min:0, max:100,
                axisLabel:{{ formatter:'{{value}}%', fontFamily:'JetBrains Mono', fontSize:9, color:'#94A3B8' }},
                splitLine:{{ lineStyle:{{ color:'#F1F5F9' }} }}
            }},
            yAxis:{{
                type:'category', data:{bar_cats_js},
                inverse:true,
                axisLabel:{{ fontFamily:'Inter', fontSize:11, color:'#475569', fontWeight:500 }},
                axisLine:{{ show:false }}, axisTick:{{ show:false }}
            }},
            series:[{{
                type:'bar',
                data: {bar_vals_js}.map(function(v,i){{
                    return {{value:v, itemStyle:{{ color:{bar_col_js}[i], borderRadius:[0,4,4,0] }}}};
                }}),
                label:{{
                    show:true, position:'right',
                    formatter: function(p){{ return p.value + '%'; }},
                    fontFamily:'JetBrains Mono', fontSize:10, color:'#475569'
                }},
                barMaxWidth:22
            }}]
        }}""", height=230, key=f"hbar_{seg['segment_index']}")

    # Full Width Image and Legend
    st.markdown('<div class="section-header" style="margin-top:20px;">Segment Frames & Evidence</div>', unsafe_allow_html=True)
    proof_frame_path = seg.get("proof_frame")
    if proof_frame_path:
        img_url = f"http://127.0.0.1:8000/{proof_frame_path}"
        st.image(
            img_url,
            caption="Proof Frame (Annotated)",
            use_container_width=True
        )
        
        # Keyword Categories Display
        colors_hex = {
            "Financial": "#00C800", "Gaming": "#0078FF", "Rewards": "#FFD700",
            "Authentication": "#E60000", "Legal": "#B432B4", "Social": "#00BEFF", "Payment_Indicator": "#FF0000"
        }
        
        detected_cats = seg.get("categorized_hits", {})
        
        # Check if there are any actual keywords found across all categories
        has_keywords = False
        if detected_cats:
            for keywords in detected_cats.values():
                if keywords:
                    has_keywords = True
                    break
                    
        top_evidence_words = []
        
        if has_keywords:
            st.markdown('<div class="section-header" style="margin-top:20px; font-size:0.9rem;">Bounding Box Evidence Legend</div>', unsafe_allow_html=True)
            cat_html = "<div style='display:flex;flex-wrap:wrap;gap:10px;margin-bottom:15px;'>"
            
            for cat, keywords in detected_cats.items():
                if not keywords:
                    continue
                kw_str = ", ".join(keywords)
                top_evidence_words.extend(keywords[:2]) # Take up to 2 from each cat for summary
                color = colors_hex.get(cat, "#333")
                display_cat = "Payment" if cat == "Payment_Indicator" else cat
                cat_html += f"""
                <div style='background:#F8FAFC;border:1px solid #E2E8F0;border-left:4px solid {color};
                border-radius:6px;padding:8px 12px;'>
                  <div style='font-family:Inter,sans-serif;font-size:0.75rem;font-weight:700;color:#1E293B;margin-bottom:2px;'>{display_cat}</div>
                  <div style='font-family:JetBrains Mono,monospace;font-size:0.7rem;color:#64748B;'>{kw_str}</div>
                </div>
                """
            cat_html += "</div>"
            st.markdown(cat_html, unsafe_allow_html=True)
            
        # --- Generate Segment Summary ---
        st.markdown('<div class="section-header" style="margin-top:20px; font-size:0.9rem;">Segment Context Summary</div>', unsafe_allow_html=True)
        
        bet_score = bet_scores[st.session_state.seg_idx_sel] if st.session_state.seg_idx_sel < len(bet_scores) else 0
        bank_score = seg.get("banking_context", 0) or 0
        
        bullets = []
        
        # Primary Intent (Betting)
        if bet_score > 70:
            bullets.append(f"<li>🎯 <strong>Primary Intent:</strong> High Betting Activity ({bet_score:.1f}% Confidence)</li>")
        elif bet_score > 30:
            bullets.append(f"<li>🎯 <strong>Primary Intent:</strong> Moderate Betting Relevance ({bet_score:.1f}% Confidence)</li>")
            
        # Financial Context
        if bank_score > 50:
            bullets.append(f"<li>💰 <strong>Financial Context:</strong> Active Payment/Banking UI Detected ({bank_score:.1f}% Confidence)</li>")
        elif seg.get("qr_detected"):
            bullets.append(f"<li>💰 <strong>Financial Context:</strong> QR Code (likely payment-related) Detected</li>")
            
        # Visual Evidence
        if top_evidence_words:
            unique_top = list(set(top_evidence_words))[:5]
            evidence_str = "', '".join(unique_top)
            bullets.append(f"<li>📸 <strong>Visual Evidence:</strong> Found '{evidence_str}'</li>")
            
        # Critical Event (Transaction Executed flag from engine)
        if seg.get("transaction_executed", 0) > 50:
            bullets.append(f"<li style='color:#DC2626;'>🚨 <strong>Critical Event:</strong> A financial transaction was likely executed in this frame.</li>")
        elif seg.get("transaction_likely", 0) > 50:
            bullets.append(f"<li style='color:#D97706;'>⚠️ <strong>Warning:</strong> User is actively attempting a financial transaction.</li>")
            
        if not bullets:
            bullets.append("<li>ℹ️ <strong>Context:</strong> General UI navigation with minimal financial or betting indicators.</li>")
            
        bullets_html = "".join(bullets)
        
        st.markdown(f"""
        <div style='background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:16px;margin-bottom:20px;'>
          <ul style='font-family:Inter,sans-serif;font-size:0.9rem;color:#166534;line-height:1.8;margin:0;padding-left:20px;'>
            {bullets_html}
          </ul>
        </div>
        """, unsafe_allow_html=True)

        # Downloads Row
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            if os.path.exists(proof_frame_path):
                with open(proof_frame_path, "rb") as f:
                    st.download_button(
                        label="📷 Download Segment Image",
                        data=f,
                        file_name=f"segment_{seg['segment_index']}_frame.jpg",
                        mime="image/jpeg",
                        use_container_width=True
                    )
        with dl_col2:
            try:
                pdf_data = create_pdf_report(seg, proof_frame_path)
                st.download_button(
                    label="📄 Download Segment PDF Report",
                    data=pdf_data,
                    file_name=f"segment_{seg['segment_index']}_report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"PDF Error: {e}")
        
        # OCR Text Expander
        with st.expander("🔍 View Raw OCR Text"):
            st.markdown(f"<div style='font-family:monospace;font-size:0.8rem;white-space:pre-wrap;background:#F1F5F9;padding:12px;border-radius:8px;border:1px solid #E2E8F0;'>{seg.get('ocr_text', 'No text detected')}</div>", unsafe_allow_html=True)
        
        # Synced Video Playback
        st.markdown('<div class="section-header" style="margin-top:20px;">Video Playback Sync</div>', unsafe_allow_html=True)
        video_path = os.path.join("uploads", original_filename)
        if os.path.exists(video_path):
            st.video(video_path, start_time=int(seg['start_time']))
        else:
            st.info("Original video file not found on server for playback.")

    else:
        st.markdown("<div style='color:#94A3B8;font-family:JetBrains Mono,monospace;font-size:0.78rem;'>No proof frame available.</div>", unsafe_allow_html=True)
        
    legend_html = """
    <div style='margin-top:20px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:15px;'>
      <div style='font-family:JetBrains Mono,monospace;font-size:0.65rem;color:#64748B;margin-bottom:12px;text-transform:uppercase;letter-spacing:0.08em;font-weight:700;'>Bounding Box Legend</div>
      <div style='display:flex;flex-wrap:wrap;gap:12px;'>
    """
    for cat, color in colors_hex.items():
        legend_html += f"<div style='display:flex;align-items:center;font-family:Inter,sans-serif;font-size:0.75rem;color:#1E293B;font-weight:500;'><div style='width:14px;height:14px;border-radius:4px;background-color:{color};margin-right:6px;box-shadow:0 1px 3px rgba(0,0,0,0.1);'></div>{cat}</div>"
    legend_html += "</div></div>"
    st.markdown(legend_html, unsafe_allow_html=True)
    # Full segment list
    st.markdown('<div class="section-header">All Segments</div>', unsafe_allow_html=True)
    filter_options = ["All","Banking","Crypto","Transaction","QR Detected","No Activity"]
    filt = st.selectbox("Filter by type", filter_options)

    filtered = verdicts
    if filt == "Banking":     filtered = [v for v in verdicts if (v.get("banking_context") or 0) > 30]
    elif filt == "Crypto":    filtered = [v for v in verdicts if (v.get("crypto_context") or 0) > 30]
    elif filt == "Transaction": filtered = [v for v in verdicts if (v.get("transaction_likely") or 0) > 30]
    elif filt == "QR Detected": filtered = [v for v in verdicts if v.get("qr_detected")]
    elif filt == "No Activity": filtered = [v for v in verdicts if
        (v.get("banking_context") or 0) <= 10 and (v.get("crypto_context") or 0) <= 10 and
        (v.get("transaction_likely") or 0) <= 10 and not v.get("qr_detected")]

    for v in filtered:
        lbl  = seg_label(v)
        vc   = seg_color(v)
        si   = v["segment_index"] - 1
        b_sc = bet_scores[si] if si < len(bet_scores) else 0

        qr_b   = '<span class="kpi-badge badge-qr">QR</span>'   if v.get("qr_detected")        else ""
        fail_b = '<span class="kpi-badge badge-fail">FAILED</span>' if v.get("transaction_failed") else ""
        bet_b  = f'<span class="kpi-badge badge-betting">BET {b_sc:.0f}</span>' if b_sc > 0 else ""

        st.markdown(f"""
        <div class='verdict-row'>
          <span class='seg-num'>#{v['segment_index']}</span>
          <span class='seg-time'>{v['start_time']:.2f}s–{v['end_time']:.2f}s</span>
          <span class='seg-verdict' style='color:{vc};'>{lbl}</span>
          {qr_b}{fail_b}{bet_b}
        </div>""", unsafe_allow_html=True)


# ═══════════════════════════ TAB 6: REPORTS ════════════════════════
with tabs[5]:
    
    # 1. Calculate Verdict
    has_betting = any(s > 50 for s in bet_scores)
    has_transactions = len(bet_tx) > 0 or len(crypto_tx) > 0
    
    if has_betting and has_transactions:
        verdict_status = "FAIL"
        verdict_title = "CRITICAL RISK - Illegal Betting Application with Active Transactions Detected"
        verdict_color = "background:#FEE2E2; color:#7F1D1D; border:2px solid #FECACA;"
        icon = "🚨"
    elif has_betting or has_transactions or len(qr_segments) > 0:
        verdict_status = "WARNING"
        verdict_title = "MEDIUM RISK - Suspicious Keywords or Payment Mechanisms Found"
        verdict_color = "background:#FFF7ED; color:#7C2D12; border:2px solid #FED7AA;"
        icon = "⚠️"
    else:
        verdict_status = "PASS"
        verdict_title = "LOW RISK - No Major Violations Detected"
        verdict_color = "background:#D1FAE5; color:#064E3B; border:2px solid #A7F3D0;"
        icon = "✅"
        
    st.markdown(f"""
    <div style="{verdict_color} border-radius:10px; padding:24px; margin-bottom:30px; display:flex; gap:20px; align-items:flex-start;">
        <div style="font-size:40px; line-height:1;">{icon}</div>
        <div>
            <div style="font-size:0.75rem; font-weight:800; letter-spacing:0.1em; opacity:0.8; margin-bottom:5px;">
                FINAL COMPLIANCE VERDICT: {verdict_status}
            </div>
            <div style="font-size:1.4rem; font-weight:900; margin-bottom:10px;">
                {verdict_title}
            </div>
            <div style="font-size:0.9rem; font-weight:500; opacity:0.9;">
                Analysis analyzed {segment_count} video segments. 
                Found {len(qr_segments)} QR codes, {len(bet_tx)} fiat transaction attempts, and {len(crypto_tx)} crypto transaction attempts.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown('<div class="section-header" style="margin-top:0;">Key Evidence Findings</div>', unsafe_allow_html=True)
        
        # Key Evidence Table
        key_evidence = [s for s in verdicts if 
            (s.get("betting_score", 0) > 50) or 
            (s.get("transaction_likely", 0) > 50) or 
            s.get("qr_detected") or 
            (s.get("transaction_executed", 0) > 0)
        ]
        # Calculate max score for sorting
        for s in key_evidence:
            s['_max_score'] = max(s.get("transaction_executed", 0) or 0, s.get("transaction_likely", 0) or 0, s.get("betting_score", 0) or 0)
            
        key_evidence = sorted(key_evidence, key=lambda x: x['_max_score'], reverse=True)[:10]
        
        if key_evidence:
            table_html = (
                '<div style="border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; background:#FFF;">'
                '<table style="width:100%; text-align:left; border-collapse:collapse; font-size:14px; font-family:Inter,sans-serif;">'
                '<thead style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569;">'
                '<tr>'
                '<th style="padding:12px;">Time</th>'
                '<th style="padding:12px;">Violation Signal</th>'
                '<th style="padding:12px;">Score</th>'
                '<th style="padding:12px;">Extracted OCR Proof</th>'
                '</tr>'
                '</thead>'
                '<tbody style="font-family:JetBrains Mono,monospace;">'
            )
            for seg in key_evidence:
                if (seg.get("transaction_executed", 0) or 0) > 50: signal = "Transaction Executed"
                elif seg.get("qr_detected"): signal = "QR Payment Code"
                elif (seg.get("transaction_likely", 0) or 0) > 50: signal = "Transaction Context"
                elif (seg.get("betting_score", 0) or 0) > 50: signal = "Betting UI"
                else: signal = "Suspicious Activity"
                
                ocr_text = seg.get("ocr_text", "")
                if len(ocr_text) > 40: ocr_text = ocr_text[:40] + "..."
                
                table_html += (
                    '<tr style="border-bottom:1px solid #F1F5F9;">'
                    f'<td style="padding:12px; color:#64748B;">{seg.get("start_time", 0):.1f}s - {seg.get("end_time", 0):.1f}s</td>'
                    f'<td style="padding:12px; color:#1E293B; font-weight:600; font-family:Inter,sans-serif;">{signal}</td>'
                    f'<td style="padding:12px; color:#DC2626; font-weight:700;">{seg["_max_score"]:.0f}%</td>'
                    f'<td style="padding:12px; font-size:11px; color:#64748B;">{ocr_text or "No text"}</td>'
                    '</tr>'
                )
            table_html += "</tbody></table></div>"
            st.markdown(table_html, unsafe_allow_html=True)
        else:
            st.markdown("<div style='padding:24px; border:1px solid #E2E8F0; border-radius:8px; text-align:center; color:#64748B;'>No significant violations found.</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-header" style="margin-top:0;">Attributed Transaction Flows</div>', unsafe_allow_html=True)
        
        # Fiat Flow
        st.markdown("<b style='font-family:Inter,sans-serif; color:#475569; font-size:14px;'>Fiat Payment Flow</b>", unsafe_allow_html=True)
        if bet_tx:
            for tx in bet_tx:
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; padding:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; margin-bottom:12px;">
                    <div style="text-align:center; padding:8px; background:#FFF; border:1px solid #E2E8F0; border-radius:6px; flex-shrink:0;">
                        <div style="font-size:10px; font-weight:700; color:#94A3B8;">BETTING UI</div>
                        <div style="font-family:JetBrains Mono,monospace; font-size:12px; font-weight:700; color:#D97706;">Detected</div>
                    </div>
                    <div style="color:#94A3B8;">→</div>
                    <div style="text-align:center; padding:8px; background:#FFF; border:1px solid #E2E8F0; border-radius:6px; flex-shrink:0;">
                        <div style="font-size:10px; font-weight:700; color:#94A3B8;">QR / INTENT</div>
                        <div style="font-family:JetBrains Mono,monospace; font-size:12px; font-weight:700; color:#0891B2;">Scanned</div>
                    </div>
                    <div style="color:#94A3B8;">→</div>
                    <div style="text-align:center; padding:8px; background:#FEE2E2; border:1px solid #FECACA; border-radius:6px; flex:1;">
                        <div style="font-size:10px; font-weight:700; color:#7F1D1D;">TRANSACTION ATTEMPT</div>
                        <div style="font-family:JetBrains Mono,monospace; font-size:12px; font-weight:700; color:#991B1B;">{tx.get('transaction_time', '')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#94A3B8; font-size:13px; font-style:italic; margin-bottom:20px;'>No fiat transactions attributed.</div>", unsafe_allow_html=True)
            
        # Crypto Flow
        st.markdown("<b style='font-family:Inter,sans-serif; color:#475569; font-size:14px;'>Crypto Flow</b>", unsafe_allow_html=True)
        if crypto_tx:
            for tx in crypto_tx:
                is_linked = tx.get('decision') == 'LINKED'
                bg_color = "#FEE2E2" if is_linked else "#FFFBEB"
                border_color = "#FECACA" if is_linked else "#FDE68A"
                text_color = "#7F1D1D" if is_linked else "#92400E"
                val_color = "#991B1B" if is_linked else "#B45309"
                
                st.markdown(f"""
                <div style="display:flex; align-items:center; gap:8px; padding:12px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; margin-bottom:12px;">
                    <div style="text-align:center; padding:8px; background:#FFF; border:1px solid #E2E8F0; border-radius:6px; flex-shrink:0;">
                        <div style="font-size:10px; font-weight:700; color:#94A3B8;">CRYPTO CONTEXT</div>
                        <div style="font-family:JetBrains Mono,monospace; font-size:12px; font-weight:700; color:#7C3AED;">Score: {tx.get('crypto_support', 0):.0f}</div>
                    </div>
                    <div style="color:#94A3B8;">→</div>
                    <div style="text-align:center; padding:8px; background:{bg_color}; border:1px solid {border_color}; border-radius:6px; flex:1;">
                        <div style="font-size:10px; font-weight:700; color:{text_color};">VERDICT: {tx.get('decision', '')}</div>
                        <div style="font-family:JetBrains Mono,monospace; font-size:12px; font-weight:700; color:{val_color};">Conf: {tx.get('confidence', 0)}%</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#94A3B8; font-size:13px; font-style:italic;'>No crypto transactions attributed.</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">Raw Data Audit Logs</div>', unsafe_allow_html=True)
    
    audit_tabs = st.tabs(["Segment Ledger", "Fiat Audit", "Crypto Audit", "JSON Downloads"])
    
    with audit_tabs[0]:
        table_html = (
            '<div style="border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; background:#FFF; max-height:500px; overflow-y:auto;">'
            '<table style="width:100%; text-align:left; border-collapse:collapse; font-size:12px; font-family:Inter,sans-serif;">'
            '<thead style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569; position:sticky; top:0;">'
            '<tr>'
            '<th style="padding:10px;">Seg # (Time)</th>'
            '<th style="padding:10px;">OCR Snippet</th>'
            '<th style="padding:10px; text-align:center;">Bank %</th>'
            '<th style="padding:10px; text-align:center;">Crypto %</th>'
            '<th style="padding:10px; text-align:center;">Tx Likely %</th>'
            '<th style="padding:10px; text-align:center;">Tx Exec %</th>'
            '<th style="padding:10px; text-align:center;">Bet Score</th>'
            '<th style="padding:10px; text-align:center;">QR?</th>'
            '</tr>'
            '</thead>'
            '<tbody style="font-family:JetBrains Mono,monospace;">'
        )
        for idx, seg in enumerate(verdicts):
            bScore = bet_scores[idx] if idx < len(bet_scores) else 0
            bank_style = "color:#0891B2; font-weight:bold; background:#ECFEFF;" if (seg.get("banking_context", 0) or 0) > 50 else "color:#94A3B8;"
            crypto_style = "color:#7C3AED; font-weight:bold; background:#F5F3FF;" if (seg.get("crypto_context", 0) or 0) > 50 else "color:#94A3B8;"
            txl_style = "color:#DC2626; font-weight:bold; background:#FEF2F2;" if (seg.get("transaction_likely", 0) or 0) > 50 else "color:#94A3B8;"
            txe_style = "color:#059669; font-weight:bold; background:#ECFDF5;" if (seg.get("transaction_executed", 0) or 0) > 50 else "color:#94A3B8;"
            bet_style = "color:#D97706; font-weight:bold; background:#FFFBEB;" if bScore > 50 else "color:#94A3B8;"
            qr_style = "<span style='background:#FEF3C7; color:#92400E; padding:2px 6px; border-radius:4px; font-size:10px; font-weight:bold;'>YES</span>" if seg.get("qr_detected") else "<span style='color:#CBD5E1;'>-</span>"
            
            ocr_text = seg.get("ocr_text", "")
            if len(ocr_text) > 30: ocr_text = ocr_text[:30] + "..."
            
            table_html += (
                '<tr style="border-bottom:1px solid #F1F5F9; hover:background:#F8FAFC;">'
                f'<td style="padding:10px; color:#64748B; white-space:nowrap;"><span style="font-weight:bold; color:#334155;">#{seg.get("segment_index", "?")}</span> <br/>{seg.get("start_time", 0):.1f}s - {seg.get("end_time", 0):.1f}s</td>'
                f'<td style="padding:10px; color:#64748B; font-size:10px;" title="{seg.get("ocr_text", "")}">{ocr_text or "-"}</td>'
                f'<td style="padding:10px; text-align:center; {bank_style}">{seg.get("banking_context", 0) or 0}%</td>'
                f'<td style="padding:10px; text-align:center; {crypto_style}">{seg.get("crypto_context", 0) or 0}%</td>'
                f'<td style="padding:10px; text-align:center; {txl_style}">{seg.get("transaction_likely", 0) or 0}%</td>'
                f'<td style="padding:10px; text-align:center; {txe_style}">{seg.get("transaction_executed", 0) or 0}%</td>'
                f'<td style="padding:10px; text-align:center; {bet_style}">{bScore}%</td>'
                f'<td style="padding:10px; text-align:center;">{qr_style}</td>'
                '</tr>'
            )
        table_html += "</tbody></table></div>"
        st.markdown(table_html, unsafe_allow_html=True)

    with audit_tabs[1]:
        if bet_tx:
            fiat_html = (
                '<div style="border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; background:#FFF;">'
                '<table style="width:100%; text-align:left; border-collapse:collapse; font-size:13px; font-family:Inter,sans-serif;">'
                '<thead style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569;">'
                '<tr><th style="padding:12px;">Time Window</th><th style="padding:12px;">Status</th><th style="padding:12px;">Linked to Betting?</th></tr>'
                '</thead><tbody style="font-family:JetBrains Mono,monospace;">'
            )
            for tx in bet_tx:
                is_bet = tx.get("transaction_used_for_betting")
                row_bg = "background:#FEF2F2;" if is_bet else ""
                status_txt = "Executed" if is_bet else "Attempted"
                link_html = "<span style='background:#FEE2E2; color:#7F1D1D; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold;'>YES - VIOLATION</span>" if is_bet else "<span style='color:#D97706; font-weight:bold;'>Attempted / Unknown</span>"
                
                fiat_html += f'<tr style="border-bottom:1px solid #F1F5F9; {row_bg}">'
                fiat_html += f'<td style="padding:12px; color:#334155; font-weight:bold;">{tx.get("transaction_time", "")}</td>'
                fiat_html += f'<td style="padding:12px; color:#64748B;">{status_txt}</td>'
                fiat_html += f'<td style="padding:12px;">{link_html}</td></tr>'
            fiat_html += "</tbody></table></div>"
            st.markdown(fiat_html, unsafe_allow_html=True)
        else:
            st.info("No fiat transactions recorded.")
            
    with audit_tabs[2]:
        if crypto_tx:
            cryp_html = (
                '<div style="border:1px solid #E2E8F0; border-radius:8px; overflow:hidden; background:#FFF;">'
                '<table style="width:100%; text-align:left; border-collapse:collapse; font-size:13px; font-family:Inter,sans-serif;">'
                '<thead style="background:#F8FAFC; border-bottom:1px solid #E2E8F0; color:#475569;">'
                '<tr><th style="padding:12px;">Segment Index</th><th style="padding:12px;">Crypto Support</th><th style="padding:12px;">Betting Purpose</th><th style="padding:12px;">AI Decision</th><th style="padding:12px;">Confidence</th></tr>'
                '</thead><tbody style="font-family:JetBrains Mono,monospace;">'
            )
            for tx in crypto_tx:
                is_linked = tx.get("decision") == "LINKED"
                row_bg = "background:#FEF2F2;" if is_linked else ""
                dec_html = f"<span style='background:#FEE2E2; color:#7F1D1D; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold;'>{tx.get('decision')}</span>" if is_linked else f"<span style='background:#FEF3C7; color:#92400E; padding:4px 8px; border-radius:4px; font-size:11px; font-weight:bold;'>{tx.get('decision')}</span>"
                
                cryp_html += f'<tr style="border-bottom:1px solid #F1F5F9; {row_bg}">'
                cryp_html += f'<td style="padding:12px; color:#334155; font-weight:bold;">#{tx.get("segment_index", "?")}</td>'
                cryp_html += f'<td style="padding:12px; color:#7C3AED; font-weight:bold;">{tx.get("crypto_support", 0):.0f}%</td>'
                cryp_html += f'<td style="padding:12px; color:#D97706; font-weight:bold;">{tx.get("betting_purpose", 0):.0f}%</td>'
                cryp_html += f'<td style="padding:12px;">{dec_html}</td>'
                cryp_html += f'<td style="padding:12px; color:#64748B; font-weight:bold;">{tx.get("confidence", 0)}%</td></tr>'
            cryp_html += "</tbody></table></div>"
            st.markdown(cryp_html, unsafe_allow_html=True)
        else:
            st.info("No crypto transactions recorded.")

    with audit_tabs[3]:
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.download_button("⬇ segment_verdicts.json",
                data=json.dumps(verdicts, indent=2),
                file_name="segment_verdicts.json", mime="application/json", use_container_width=True)
        with c2:
            st.download_button("⬇ betting_scores.json",
                data=json.dumps(bet_scores, indent=2),
                file_name="betting_scores.json", mime="application/json", use_container_width=True)
        with c3:
            st.download_button("⬇ betting_tx_attr.json",
                data=json.dumps(bet_tx, indent=2),
                file_name="betting_tx_attr.json", mime="application/json", use_container_width=True)
        with c4:
            st.download_button("⬇ crypto_tx_attr.json",
                data=json.dumps(crypto_tx, indent=2),
                file_name="crypto_tx_attr.json", mime="application/json", use_container_width=True)

