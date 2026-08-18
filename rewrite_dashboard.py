import re

def rewrite_dashboard():
    with open('dashboard.py', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Add imports
    content = content.replace(
        "import sys\nfrom pathlib import Path",
        "import sys\nimport os\nimport tempfile\nfrom pathlib import Path\nfrom extractframes import extractFrames"
    )

    # 2. Replace CSS block
    css_start = content.find("st.markdown(\"\"\"\n<style>")
    css_end = content.find("</style>\n\"\"\", unsafe_allow_html=True)") + len("</style>\n\"\"\", unsafe_allow_html=True)")
    
    new_css = '''st.markdown("""
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
""", unsafe_allow_html=True)'''

    content = content[:css_start] + new_css + content[css_end:]

    # 3. Replace Sidebar Logic
    sidebar_start = content.find("with st.sidebar:")
    sidebar_end = content.find("output_path = Path(output_dir)")
    
    new_sidebar = '''with st.sidebar:
    st.markdown("### 🎬 Video Intel Dashboard")
    
    st.markdown("#### Upload Video")
    uploaded_file = st.file_uploader("Analyze a new video", type=["mp4", "mov", "avi"])
    if uploaded_file is not None:
        if st.button("Start Analysis", type="primary"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                tmp_file.write(uploaded_file.read())
                temp_video_path = tmp_file.name
            
            with st.status("Analyzing Video...", expanded=True) as status:
                st.write("Extracting frames and identifying signals...")
                progress_bar = st.progress(0.0, text="Processing: 0%")
                
                def update_progress(val):
                    progress_bar.progress(val, text=f"Processing: {int(val * 100)}%")
                
                try:
                    extractFrames(temp_video_path, progress_callback=update_progress)
                    video_name = os.path.splitext(os.path.basename(temp_video_path))[0]
                    st.session_state.output_dir = os.path.join("outputs", video_name)
                    status.update(label="Analysis Complete!", state="complete", expanded=False)
                    st.rerun()
                except Exception as e:
                    status.update(label="Analysis Failed", state="error", expanded=False)
                    st.error(f"Error during analysis: {e}")
                finally:
                    if os.path.exists(temp_video_path):
                        os.remove(temp_video_path)

    st.markdown("---")
    st.markdown("#### Select Existing Analysis")
    
    # Check outputs directory
    outputs_dir = Path("outputs")
    existing_outputs = [d.name for d in outputs_dir.iterdir() if d.is_dir()] if outputs_dir.exists() else []
    
    if "output_dir" not in st.session_state:
        st.session_state.output_dir = cli_dir or (f"outputs/{existing_outputs[0]}" if existing_outputs else "")
        
    options = [f"outputs/{d}" for d in existing_outputs]
    if cli_dir and cli_dir not in options:
        options.append(cli_dir)

    selected_output = st.selectbox(
        "Previous Analyses", 
        options=options,
        index=0 if options else None
    )
    
    if selected_output and selected_output != st.session_state.output_dir:
        st.session_state.output_dir = selected_output
        st.rerun()

output_dir = st.session_state.get("output_dir", "")
if not output_dir or not os.path.exists(output_dir):
    st.info("👈 Please upload a video to analyze or select an existing output directory from the sidebar.")
    st.stop()

'''
    
    content = content[:sidebar_start] + new_sidebar + content[sidebar_end:]

    # 4. Remove Severity Color Overlays
    severity_overlay = """    st.markdown('''
    <style>
    div[data-testid="column"]:nth-child(2) [data-testid="metric-container"]
        { border-top: 3px solid #D97706 !important; }
    div[data-testid="column"]:nth-child(3) [data-testid="metric-container"]
        { border-top: 3px solid #0891B2 !important; }
    div[data-testid="column"]:nth-child(4) [data-testid="metric-container"]
        { border-top: 3px solid #7C3AED !important; }
    div[data-testid="column"]:nth-child(5) [data-testid="metric-container"]
        { border-top: 3px solid #D97706 !important; }
    div[data-testid="column"]:nth-child(6) [data-testid="metric-container"]
        { border-top: 3px solid #DC2626 !important; }
    </style>
    ''', unsafe_allow_html=True)"""
    # Just remove it
    content = re.sub(r'st\.markdown\("""\n\s*<style>\n\s*div\[data-testid="column"\].*?</style>\n\s*""", unsafe_allow_html=True\)', '', content, flags=re.DOTALL)

    # 5. Fix executive summary replacement
    exec_summary_start = content.find("    with col_a:\n        st.markdown('<div class=\"section-header\">Executive Summary</div>', unsafe_allow_html=True)")
    exec_summary_end = content.find("    # ── Signal Coverage bars ──")
    
    new_exec_summary = '''    with col_a:
        st.markdown('<div class="section-header">Executive Summary</div>', unsafe_allow_html=True)
        with st.container(border=True):
            def exec_row(label, value):
                st.markdown(f"**{label}**: {value}")

            exec_row("Betting Coverage",       f"{betting_pct}%")
            exec_row("Max Betting Score",      f"{max_bet_score:.1f} / 100")
            exec_row("Avg Betting Score",      f"{avg_bet_score:.1f} / 100")
            exec_row("Banking Segments",       f"{len(banking_segs)} / {segment_count}")
            exec_row("Crypto Segments",        f"{len(crypto_segs)} / {segment_count}")
            exec_row("QR / Payment Events",    f"{len(qr_segments)} events")
            exec_row("High Tx Likelihood",     f"{len(tx_likely_segs)} segments")
            exec_row("Failed Transactions",    f"{len(failed_tx_times)} attempts")
            exec_row("Tx Executed",            f"{len(tx_exec_segs)} confirmed")
            exec_row("Video Duration",         f"{total_duration:.1f}s")
'''
    
    content = content[:exec_summary_start] + new_exec_summary + content[exec_summary_end:]
    
    # 6. Fix signal coverage replacement
    signal_coverage_start = content.find("    with col_b:\n        st.markdown('<div class=\"section-header\">Signal Coverage</div>', unsafe_allow_html=True)")
    signal_coverage_end = content.find("    # ── Timeline hero (full width) ──")
    
    new_signal_coverage = '''    with col_b:
        st.markdown('<div class="section-header">Signal Coverage</div>', unsafe_allow_html=True)
        with st.container(border=True):
            def signal_bar(label, count, total, color):
                pct = count / total if total else 0
                st.markdown(f"**{label}**: {count} / {total} ({pct*100:.1f}%)")
                st.progress(pct)

            signal_bar("Banking Context",     len(banking_segs),    segment_count, "#0891B2")
            signal_bar("Crypto Context",      len(crypto_segs),     segment_count, "#7C3AED")
            signal_bar("Transaction Likely",  len(tx_likely_segs),  segment_count, "#DC2626")
            signal_bar("QR Code Detected",    len(qr_segments),     segment_count, "#D97706")
            signal_bar("Betting Coverage",    len(betting_nonzero), len(bet_scores) or 1, "#F59E0B")
            signal_bar("Failed Tx",           len(failed_tx_times), max(len(bet_tx),1), "#991B1B")
'''
    content = content[:signal_coverage_start] + new_signal_coverage + content[signal_coverage_end:]
    
    with open('dashboard.py', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    rewrite_dashboard()
