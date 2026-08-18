
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
from pathlib import Path
from extractframes import extractFrames
from collections import Counter

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
    st.markdown("### 🎬 Video Intel Dashboard")
    
    st.markdown("#### Upload Video")
    uploaded_file = st.file_uploader("Analyze a new video", type=["mp4", "mov", "avi", "webm"])
    if uploaded_file is not None:
        if st.button("Start Analysis", type="primary"):
            ext = os.path.splitext(uploaded_file.name)[1] or ".mp4"
            with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
                tmp_file.write(uploaded_file.read())
                temp_video_path = tmp_file.name
            
            with st.status("Analyzing Video...", expanded=True) as status:
                st.write("Extracting frames and identifying signals...")
                progress_bar = st.progress(0.0, text="Processing: 0%")
                
                def update_progress(val):
                    progress_bar.progress(val, text=f"Processing: {int(val * 100)}%")
                
                try:
                    clean_name = re.sub(r'[^A-Za-z0-9_-]', '_', os.path.splitext(uploaded_file.name)[0])
                    extractFrames(temp_video_path, progress_callback=update_progress, video_name=clean_name)
                    st.session_state.output_dir = os.path.join("outputs", clean_name)
                    status.update(label="Analysis Complete!", state="complete", expanded=False)
                    st.rerun()
                except Exception as e:
                    import traceback
                    err_msg = traceback.format_exc()
                    status.update(label="Analysis Failed", state="error", expanded=True)
                    st.error(f"Error during analysis: {e}\n\n{err_msg}")
                finally:
                    if os.path.exists(temp_video_path):
                        os.remove(temp_video_path)

    st.markdown("---")
    st.markdown("#### Select Existing Analysis")
    
    # Check outputs directory
    outputs_dir = Path("outputs")
    existing_outputs = []
    if outputs_dir.exists():
        for d in outputs_dir.iterdir():
            if d.is_dir() and (d / "segment_verdicts.json").exists():
                existing_outputs.append(d.name)
    
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

output_path = Path(output_dir)

# ─────────────────────────── LOAD DATA ─────────────────────────────
verdicts   = load_json(output_path / "segment_verdicts.json") or []
bet_scores = load_json(output_path / "betting_segment_scores.json") or []
bet_tx     = load_json(output_path / "betting_transaction_attribution.json") or []
crypto_tx  = load_json(output_path / "crypto_betting_attribution.json") or []
summary    = load_text(output_path / "final_summary.txt")
report     = load_text(output_path / "final_verdict_report.txt")
frames_dir = output_path / "frames"

if not verdicts:
    st.error(f"No `segment_verdicts.json` found in `{output_dir}`. Check the path.")
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
  {segment_count} segments · {total_duration:.1f}s total · {len(qr_segments)} QR detections · {len(failed_tx_times)} failed transactions
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

    # ── KPI Row with severity colors ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    # Inject per-metric accent via markdown delta trick: use colored HTML in label
    c1.metric("Segments",         segment_count,              f"{total_duration:.1f}s video")
    c2.metric("QR Detected",      len(qr_segments),           f"{len(qr_segments)} events")
    c3.metric("Banking Segs",     len(banking_segs),          f"{len(banking_segs)/segment_count*100:.0f}% coverage")
    c4.metric("Crypto Segs",      len(crypto_segs),           f"{len(crypto_segs)/segment_count*100:.0f}% coverage")
    c5.metric("Betting Coverage", f"{betting_pct}%",          f"{len(betting_nonzero)} segments")
    c6.metric("Failed Tx",        len(failed_tx_times),       "unconfirmed attempts",
              delta_color="inverse" if failed_tx_times else "off")

    # Severity colour overlays via st.markdown (injects border-top on each card)
    

    st.markdown("---")

    col_a, col_b = st.columns([1, 1.2])

    # ── Executive Summary (replaces pie) ──
    with col_a:
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
    # ── Signal Coverage bars ──
    with col_b:
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
        '<div class="section-header">Transaction Event Table</div>',
        unsafe_allow_html=True
    )
    
    event_rows = []

    for tx in bet_tx:
        tx_time = tx.get("transaction_time", "")

        try:
            start_t, end_t = re.split(r"[–-]", tx_time)
            duration = round(float(end_t) - float(start_t), 2)
        except:
            start_t = end_t = duration = "N/A"

        result = (
            "Failed"
            if not tx.get("transaction_used_for_betting", False)
            else "Executed"
        )

        event_rows.append({
            "Event Type": "QR Payment",
            "Start": f"{start_t}s",
            "End": f"{end_t}s",
            "Duration": f"{duration}s",
            "Result": result
        })

    if event_rows:
        st.dataframe(
            event_rows,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No transaction events detected.")


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
    st.markdown('<div class="section-header">Segment Explorer</div>', unsafe_allow_html=True)

    col_left, col_right = st.columns([1, 2])

    with col_left:
        seg_options = [
            f"Seg {v['segment_index']:03d} | {v['start_time']:.2f}s – {v['end_time']:.2f}s"
            for v in verdicts
        ]
        selected     = st.selectbox("Select Segment", seg_options)
        seg_idx_sel  = int(selected.split("Seg ")[1].split(" ")[0]) - 1
        seg          = verdicts[seg_idx_sel]

        # Horizontal bar comparison (replaces radar)
        bank_val  = seg.get("banking_context",    0) or 0
        cryp_val  = seg.get("crypto_context",     0) or 0
        txlk_val  = seg.get("transaction_likely", 0) or 0
        txex_val  = seg.get("transaction_executed",0) or 0
        bet_val   = bet_scores[seg_idx_sel] if seg_idx_sel < len(bet_scores) else 0
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

        # Horizontal bar chart via ECharts (replaces radar)
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

        # Frames preview
        st.markdown('<div class="section-header">Segment Frames</div>', unsafe_allow_html=True)
        if frames_dir.exists():
            all_frames = sorted(frames_dir.glob("frame*.jpg"),
                                key=lambda p: int(p.stem.replace("frame","")))
            fps_est    = len(all_frames) / total_duration if total_duration > 0 else 8
            f_start    = int(seg["start_time"] * fps_est)
            f_end      = int(seg["end_time"]   * fps_est)
            seg_frames = [f for f in all_frames
                          if f_start <= int(f.stem.replace("frame","")) <= f_end]
            if not seg_frames and all_frames:
                seg_frames = [min(all_frames, key=lambda f: abs(int(f.stem.replace("frame","")) - f_start))]
            display_frames = seg_frames[:1]
            if display_frames:
                img_cols = st.columns(len(display_frames))
                for col, fp in zip(img_cols, display_frames):
                    col.image(
                        str(fp),
                        caption=fp.stem,
                        width=250   # try 200, 250, or 300
                    )
            else:
                st.markdown("<div style='color:#94A3B8;font-family:JetBrains Mono,monospace;font-size:0.78rem;'>No frames found for this segment.</div>", unsafe_allow_html=True)
        else:
            st.markdown("<div style='color:#94A3B8;font-family:JetBrains Mono,monospace;font-size:0.78rem;'>frames/ directory not found.</div>", unsafe_allow_html=True)

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
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-header">Final Summary</div>', unsafe_allow_html=True)
        if summary:
            summary_clean = "\n".join(
                line for line in summary.splitlines()
                if not (line.strip() and set(line.strip()) == {"="})
            )

            st.markdown(f"""
            <div style='background:#FAFAFA;
            border:1px solid #E2E8F0;
            border-radius:10px;
            padding:20px;
            font-family:Inter,sans-serif;
            font-size:15px;
            line-height:1.8;
            color:#334155;
            white-space:pre-wrap;
            max-height:500px;
            overflow-y:auto;'>{summary_clean}</div>
            """, unsafe_allow_html=True)
        else:
            st.info("final_summary.txt not found.")

    with col2:
        st.markdown('<div class="section-header">Verdict Report Preview</div>', unsafe_allow_html=True)
        if report:
            report_clean = "\n".join(
                line for line in report.splitlines()
                if not (line.strip() and set(line.strip()) == {"="})
            )

            st.markdown(f"""
            <div style='background:#FAFAFA;
            border:1px solid #E2E8F0;
            border-radius:10px;
            padding:20px;
            font-family:Inter,sans-serif;
            font-size:132x;
            line-height:1.4;
            color:#334155;
            white-space:pre-wrap;
            max-height:500px;
            overflow-y:auto;'>{report_clean}</div>
            """, unsafe_allow_html=True)
        else:
            st.info("final_verdict_report.txt not found.")

    if crypto_tx:
        st.markdown('<div class="section-header">Crypto Betting Attribution</div>', unsafe_allow_html=True)
        st.json(crypto_tx)
    else:
        st.markdown("""<div class='verdict-row' style='color:#94A3B8;margin-top:20px;'>
          No crypto betting attribution data (crypto_betting_attribution.json is empty).
        </div>""", unsafe_allow_html=True)

    with st.expander("📦 Raw Data Export"):
        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇ segment_verdicts.json",
                data=json.dumps(verdicts, indent=2),
                file_name="segment_verdicts.json", mime="application/json")
            st.download_button("⬇ betting_segment_scores.json",
                data=json.dumps(bet_scores, indent=2),
                file_name="betting_segment_scores.json", mime="application/json")
        with c2:
            st.download_button("⬇ betting_transaction_attribution.json",
                data=json.dumps(bet_tx, indent=2),
                file_name="betting_transaction_attribution.json", mime="application/json")
            st.download_button("⬇ crypto_betting_attribution.json",
                data=json.dumps(crypto_tx, indent=2),
                file_name="crypto_betting_attribution.json", mime="application/json")
