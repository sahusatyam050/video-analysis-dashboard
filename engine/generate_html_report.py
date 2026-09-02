import os
import json
import base64

def _image_to_base64(img_path):
    if img_path and os.path.exists(img_path):
        try:
            with open(img_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                ext = os.path.splitext(img_path)[1].lstrip(".").lower()
                mime = "image/jpeg" if ext in ["jpg", "jpeg"] else f"image/{ext}"
                return f"data:{mime};base64,{encoded}"
        except Exception:
            pass
    return ""

def generate_html_report(output_dir, task_id=None, complaint_id=None):
    """
    Generates a standalone, beautifully styled HTML evidence report (evidence_report.html).
    """
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "evidence_report.html")

    # Load data files
    verdict_txt = ""
    txt_path = os.path.join(output_dir, "final_summary.txt")
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8") as f:
            verdict_txt = f.read()

    segments_data = []
    seg_json_path = os.path.join(output_dir, "segment_verdicts.json")
    if os.path.exists(seg_json_path):
        with open(seg_json_path, "r", encoding="utf-8") as f:
            segments_data = json.load(f)

    # Build HTML rows for segments
    segments_html = ""
    for seg in segments_data:
        idx = seg.get("segment_index", 1)
        start = seg.get("start_time", 0.0)
        end = seg.get("end_time", 0.0)
        proof = seg.get("proof_frame", "")
        img_b64 = _image_to_base64(proof)
        ai_summary = seg.get("ai_summary", "General screen navigation")
        banking = seg.get("banking_context", 0.0)
        crypto = seg.get("crypto_context", 0.0)
        likely = seg.get("transaction_likely", 0.0)
        qr = seg.get("qr_detected", False)

        img_tag = f'<img src="{img_b64}" style="max-width:280px; border-radius:6px; border:1px solid #334155;" />' if img_b64 else '<span style="color:#94a3b8;">[No Proof Frame]</span>'

        segments_html += f"""
        <div style="background:#1e293b; border:1px solid #334155; border-radius:8px; padding:16px; margin-bottom:16px; display:flex; gap:20px; align-items:flex-start;">
            <div style="flex:0 0 280px; text-align:center;">
                {img_tag}
                <div style="font-size:12px; color:#94a3b8; margin-top:6px;">Segment #{idx} ({start:.1f}s – {end:.1f}s)</div>
            </div>
            <div style="flex:1;">
                <h4 style="margin:0 0 8px 0; color:#38bdf8;">Segment #{idx} Breakdown</h4>
                <div style="background:#0f172a; border-left:4px solid #38bdf8; padding:10px 14px; border-radius:4px; font-size:14px; margin-bottom:12px;">
                    <strong>AI Forensic Summary:</strong> {ai_summary}
                </div>
                <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; font-size:13px;">
                    <div style="background:#0f172a; padding:8px; border-radius:4px; text-align:center;">
                        <span style="color:#94a3b8; display:block; font-size:11px;">Banking Context</span>
                        <strong style="color:#22c55e;">{banking:.1f}%</strong>
                    </div>
                    <div style="background:#0f172a; padding:8px; border-radius:4px; text-align:center;">
                        <span style="color:#94a3b8; display:block; font-size:11px;">Crypto Context</span>
                        <strong style="color:#a855f7;">{crypto:.1f}%</strong>
                    </div>
                    <div style="background:#0f172a; padding:8px; border-radius:4px; text-align:center;">
                        <span style="color:#94a3b8; display:block; font-size:11px;">Txn Likelihood</span>
                        <strong style="color:#eab308;">{likely:.1f}%</strong>
                    </div>
                    <div style="background:#0f172a; padding:8px; border-radius:4px; text-align:center;">
                        <span style="color:#94a3b8; display:block; font-size:11px;">QR Detected</span>
                        <strong style="color:{'#22c55e' if qr else '#94a3b8'};">{'YES' if qr else 'NO'}</strong>
                    </div>
                </div>
            </div>
        </div>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Forensic Evidence Report - Task #{task_id or 'N/A'}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #0f172a; color: #f8fafc; margin: 0; padding: 30px; }}
        .container {{ max-width: 1000px; margin: 0 auto; }}
        .header {{ border-bottom: 2px solid #38bdf8; padding-bottom: 15px; margin-bottom: 25px; display:flex; justify-content:space-between; align-items:center; }}
        .header h1 {{ margin: 0; color: #38bdf8; font-size: 24px; }}
        .badge {{ background: #0284c7; color: white; padding: 4px 12px; border-radius: 9999px; font-size: 13px; font-weight: bold; }}
        .section {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 20px; margin-bottom: 25px; }}
        .section h2 {{ margin-top: 0; color: #f1f5f9; font-size: 18px; border-bottom: 1px solid #334155; padding-bottom: 8px; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; font-family: inherit; font-size: 14px; color: #cbd5e1; line-height: 1.6; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>🛡️ Forensic Video Evidence Report</h1>
                <div style="color: #94a3b8; font-size: 14px; margin-top: 4px;">Task ID: #{task_id or 'N/A'} | Complaint ID: {complaint_id or 'N/A'}</div>
            </div>
            <div class="badge">COURT EVIDENTIARY RECORD</div>
        </div>

        <div class="section">
            <h2>📜 Executive Case Summary & Verdict</h2>
            <pre>{verdict_txt or 'Executive summary not generated.'}</pre>
        </div>

        <div class="section">
            <h2>📸 Segment Evidence Breakdown & AI Screenshot Summaries</h2>
            {segments_html or '<p style="color:#94a3b8;">No segment evidence available.</p>'}
        </div>
    </div>
</body>
</html>
"""

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    return out_path
