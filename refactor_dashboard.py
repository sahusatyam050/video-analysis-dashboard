import re

with open("dashboard.py", "r") as f:
    content = f.read()

# Define the new Sidebar
new_sidebar = """with st.sidebar:
    st.markdown('''
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:24px; margin-top:-10px;">
            <div style="background:#0F172A; width:38px; height:38px; display:flex; align-items:center; justify-content:center; border-radius:10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                <span style="font-size:18px;">🤖</span>
            </div>
            <div style="display:flex; flex-direction:column; justify-content:center;">
                <span style="font-family:Inter,sans-serif; font-size:17px; font-weight:800; color:#0F172A; line-height:1.2; letter-spacing:-0.03em;">Command Center</span>
                <span style="font-family:Inter,sans-serif; font-size:11px; font-weight:600; color:#64748B; text-transform:uppercase; letter-spacing:0.05em; line-height:1.2; margin-top:2px;">Forensic Crawler</span>
            </div>
        </div>
    ''', unsafe_allow_html=True)
    
    st.markdown("#### Select Existing Analysis")
    
    # Check existing outputs via API
"""

# Find where the sidebar starts and the API check starts
start_idx = content.find("with st.sidebar:")
end_idx = content.find("    # Check existing outputs via API")

# Replace everything from `with st.sidebar:` down to the API check
content = content[:start_idx] + new_sidebar + content[end_idx+37:]

# Now replace the 'No Analysis Selected' block (lines 517-536) with the Command Center UI
no_analysis_start = content.find('output_dir = st.session_state.get("output_dir", "")\nif not output_dir:')
no_analysis_end = content.find('output_path = Path(output_dir)')

command_center_ui = """output_dir = st.session_state.get("output_dir", "")
if not output_dir:
    import time
    st.markdown("<h2 style='text-align: center; margin-bottom: 2rem;'>🚀 Forensic Command Center</h2>", unsafe_allow_html=True)
    
    if "active_crawl_task" not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("### 🌐 Launch Autonomous Agent")
            crawl_url = st.text_input("Target Website URL", placeholder="https://example-betting.com")
            crawl_duration = st.slider("Crawl Duration (seconds)", min_value=10, max_value=120, value=60)
            
            if st.button("Start Autonomous Crawl", type="primary", use_container_width=True):
                if crawl_url:
                    try:
                        payload = {"url": crawl_url, "duration": crawl_duration}
                        resp = requests.post("http://127.0.0.1:8000/crawl", json=payload)
                        resp.raise_for_status()
                        st.session_state.active_crawl_task = resp.json()["task_id"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error starting crawl: {e}")
                else:
                    st.error("Please enter a URL.")
                    
            st.markdown("---")
            st.markdown("### 📂 Manual Evidence Upload")
            uploaded_file = st.file_uploader("Select Video to Analyze", type=["mp4", "mov", "avi", "webm"])
            if uploaded_file and st.button("Analyze Uploaded Video", use_container_width=True):
                try:
                    files = {'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    resp = requests.post("http://127.0.0.1:8000/analyze", files=files)
                    resp.raise_for_status()
                    st.session_state.active_crawl_task = resp.json()["task_id"] # Use same UI for polling
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        task_id = st.session_state.active_crawl_task
        try:
            status_resp = requests.get(f"http://127.0.0.1:8000/status/{task_id}")
            if status_resp.status_code == 200:
                data = status_resp.json()
                status = data.get("status")
                crawler_state = data.get("crawler_state")
                current_phase = data.get("current_phase", "init")
                
                if status == "error":
                    st.error(f"🚨 Error: {data.get('error_message')}")
                    if st.button("Clear & Restart"):
                        del st.session_state.active_crawl_task
                        st.rerun()
                elif status == "complete":
                    st.success("✅ Crawl & Analysis Complete!")
                    st.session_state.output_dir = str(task_id)
                    del st.session_state.active_crawl_task
                    st.rerun()
                else:
                    if crawler_state == "waiting_for_otp":
                        st.error("🚨 **INTERCEPT: 2FA/OTP Required to Expose Financials**", icon="🚨")
                        with st.form("otp_form"):
                            st.info("The autonomous agent has successfully injected seed credentials and bypassed initial security. A live OTP is required to unlock the final financial gateway.")
                            otp_val = st.text_input("Enter the OTP sent to the registered mobile/email")
                            if st.form_submit_button("Submit OTP to Resume") and otp_val:
                                requests.post(f"http://127.0.0.1:8000/submit_otp/{task_id}", json={"otp": otp_val})
                                st.success("OTP Accepted! Resuming forensic crawl...")
                                time.sleep(1)
                                st.rerun()
                    else:
                        st.markdown("### 🤖 Live Agent Telemetry")
                        
                        # Live Checklist Logic
                        phases = {
                            "init": 0, "auth": 1, "context": 2, "affiliate": 3, "financial": 4, "finalizing": 5
                        }
                        current_idx = phases.get(current_phase, 0)
                        
                        def get_icon(idx):
                            if current_idx > idx: return "✅"
                            if current_idx == idx: return "⏳"
                            return "⭕"
                            
                        st.markdown(f"**{get_icon(1)} Phase 1:** Bypassing Security & Authenticating")
                        st.markdown(f"**{get_icon(2)} Phase 2:** Mapping Contextual Intelligence & Behaviors")
                        st.markdown(f"**{get_icon(3)} Phase 3:** Scanning Affiliate & Promotion Networks")
                        st.markdown(f"**{get_icon(4)} Phase 4:** Exposing Financial Gateways & Triggering QR Codes")
                        st.markdown(f"**{get_icon(5)} Phase 5:** Finalizing Evidence Video & Generating Forensic Report")
                        
                        st.markdown("---")
                        st.info("The agent is actively executing operations in the background. Please wait...")
                        
                        time.sleep(1.5)
                        st.rerun()
        except Exception as e:
            st.error(f"Error checking status: {e}")
            if st.button("Clear"):
                del st.session_state.active_crawl_task
                st.rerun()
                
    st.stop()

"""
content = content[:no_analysis_start] + command_center_ui + content[no_analysis_end:]

# Add Executive Summary Metrics
tabs_start = content.find("# ─────────────────────────── TABS ──────────────────────────────────\\ntabs = st.tabs([")
exec_summary = """# ─────────────────────────── EXECUTIVE SUMMARY METRICS ──────────────
st.markdown("### Executive Intelligence Summary")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("QR/UPI Signatures", len(qr_segments), delta="High Risk", delta_color="inverse")
with col2:
    st.metric("Mule/Banking Gateways", len(banking_segs), delta="Critical", delta_color="inverse")
with col3:
    verdict_text = "Betting Confirmed" if betting_evidence else "Inconclusive"
    st.metric("Forensic Verdict", verdict_text, delta="Action Required" if betting_evidence else "Review", delta_color="inverse")
st.markdown("<br>", unsafe_allow_html=True)

"""

if "Executive Intelligence Summary" not in content:
    content = content[:tabs_start] + exec_summary + content[tabs_start:]

with open("dashboard.py", "w") as f:
    f.write(content)

print("Dashboard Refactored")
