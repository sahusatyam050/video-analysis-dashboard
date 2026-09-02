"""
generate_evidence_report.py

Reads final_summary.txt almost verbatim → produces evidence_report.pdf.
Only change: proof-image grids injected below three sections:
  - TRANSACTION FLOW OBSERVATION  → qr_segments
  - FAILED TRANSACTION ATTEMPT    → failed_segments
  - TRANSACTION EXECUTION RESULT  → executed_segments
"""

import os
import re
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image, Paragraph, SimpleDocTemplate, Spacer,
    Table, TableStyle, HRFlowable,
)

# ── Layout constants ──────────────────────────────────────────────────────────
IMG_WIDTH      = 1.5 * inch
IMG_HEIGHT     = 2.5 * inch
IMAGES_PER_ROW = 4
COL_WIDTH      = 1.6 * inch
PAGE_MARGIN    = 0.6 * inch
ACCENT         = colors.HexColor("#1a1a2e")
MUTED          = colors.HexColor("#6b6b6b")
FRAME_NUM_RE   = re.compile(r"frame(\d+)\.\w+$", re.IGNORECASE)

_QR_TRIGGER   = "transaction flow observation"
_FAIL_TRIGGER = "failed transaction attempt"
_EXEC_TRIGGER = "transaction execution"
_SUCC_TRIGGER = "successful transaction"


# ── Styles ────────────────────────────────────────────────────────────────────
def _build_styles():
    s = getSampleStyleSheet()
    s.add(ParagraphStyle("ReportTitle",    parent=s["Title"],  fontSize=13, textColor=ACCENT, spaceAfter=2, alignment=TA_LEFT))
    s.add(ParagraphStyle("SectionHeader",  parent=s["Normal"], fontSize=11, textColor=ACCENT, spaceBefore=12, spaceAfter=4, fontName="Helvetica-Bold"))
    s.add(ParagraphStyle("BodyLine",       parent=s["Normal"], fontSize=9,  leading=13, spaceAfter=1))
    s.add(ParagraphStyle("EvidenceLabel",  parent=s["Normal"], fontSize=9,  textColor=MUTED, spaceBefore=6, spaceAfter=3, fontName="Helvetica-BoldOblique"))
    s.add(ParagraphStyle("Caption",        parent=s["Normal"], fontSize=7,  alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceBefore=2))
    s.add(ParagraphStyle("MissingFrame",   parent=s["Normal"], fontSize=7,  alignment=TA_CENTER, textColor=colors.HexColor("#aa3333")))
    return s


# ── Proof-frame helpers ───────────────────────────────────────────────────────
def _ts(seg):
    return f"{seg['start_time']:.2f}s\u2013{seg['end_time']:.2f}s"

def _frame_no(path):
    if not path: return None
    m = FRAME_NUM_RE.search(path)
    return m.group(1) if m else None

def _proof_path(seg):
    p = seg.get("proof_frame")
    if p and os.path.exists(p): return p
    for f in seg.get("frames", []):
        mid = seg["frames"][len(seg["frames"]) // 2]
        if os.path.exists(mid): return mid
    return None

def _img_cell(seg, styles):
    p = _proof_path(seg)
    if p:
        try: return Image(p, width=IMG_WIDTH, height=IMG_HEIGHT)
        except Exception: pass
    return Paragraph("[proof frame unavailable]", styles["MissingFrame"])

def _cap_cell(seg, styles):
    ts = _ts(seg)
    fn = _frame_no(_proof_path(seg))
    ai_sum = seg.get("ai_summary", "")
    text = (f"Frame {fn} ({ts})" if fn else ts)
    if ai_sum:
        text += f"<br/><b>AI Summary:</b> {ai_sum}"
    return Paragraph(text, styles["Caption"])

def _image_grid(segs, styles, per_row=IMAGES_PER_ROW):
    if not segs: return None
    rows = []
    for i in range(0, len(segs), per_row):
        chunk = segs[i:i+per_row]
        ir = [_img_cell(s, styles) for s in chunk]
        cr = [_cap_cell(s, styles) for s in chunk]
        while len(ir) < per_row: ir.append(""); cr.append("")
        rows += [ir, cr]
    t = Table(rows, colWidths=[COL_WIDTH]*per_row)
    t.setStyle(TableStyle([
        ("ALIGN",         (0,0),(-1,-1),"CENTER"),
        ("VALIGN",        (0,0),(-1,-1),"TOP"),
        ("TOPPADDING",    (0,0),(-1,-1),3),
        ("BOTTOMPADDING", (0,0),(-1,-1),5),
        ("LEFTPADDING",   (0,0),(-1,-1),2),
        ("RIGHTPADDING",  (0,0),(-1,-1),2),
    ]))
    return t


# ── Section key detection ─────────────────────────────────────────────────────
def _section_key(header):
    h = header.lower()
    if _QR_TRIGGER   in h: return "qr"
    if _FAIL_TRIGGER in h: return "failed"
    if _EXEC_TRIGGER in h or _SUCC_TRIGGER in h: return "executed"
    return None

def _is_header(core):
    return (core == core.upper() and len(core) > 4
            and not core.startswith(("•", "–", "#")))


# ── Main entry point ──────────────────────────────────────────────────────────
def generate_evidence_report(
    segments, qr_segments, executed_segments, failed_segments,
    likely_segments, betting_attribution, betting_scores,
    avg_banking, avg_crypto, meaningful_betting, betting_pct,
    output_dir="outputs", video_name=None, text_report_path=None,
):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "evidence_report.pdf")

    if text_report_path is None:
        text_report_path = os.path.join(output_dir, "final_summary.txt")

    styles  = _build_styles()
    pools   = {"qr": qr_segments or [], "failed": failed_segments or [], "executed": executed_segments or []}
    story   = []

    if os.path.exists(text_report_path):
        with open(text_report_path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()

        pending   = None   # image-set key waiting to be injected
        first_txt = True

        for raw in lines:
            stripped = raw.rstrip()
            core     = stripped.strip()

            # ── Blank line ──
            if not core:
                if pending is not None:
                    pool = pools.get(pending, [])
                    if pool:
                        story.append(Paragraph("Evidence:", styles["EvidenceLabel"]))
                        g = _image_grid(pool, styles)
                        if g: story.append(g)
                    pending = None
                story.append(Spacer(1, 4))
                continue

            # ── Section header ──
            if _is_header(core):
                if pending is not None:
                    pool = pools.get(pending, [])
                    if pool:
                        story.append(Paragraph("Evidence:", styles["EvidenceLabel"]))
                        g = _image_grid(pool, styles)
                        if g: story.append(g)
                    pending = None
                story.append(Paragraph(core, styles["SectionHeader"]))
                story.append(HRFlowable(width="100%", thickness=0.5, color=ACCENT, spaceAfter=4))
                key = _section_key(core)
                if key: pending = key
                continue

            # ── Report title (first non-blank, non-header line) ──
            if first_txt:
                story.append(Paragraph(core, styles["ReportTitle"]))
                first_txt = False
                continue

            # ── Ordinary body line ──
            indent = (len(stripped) - len(core)) * 5
            safe   = core.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
            p_sty  = ParagraphStyle("DynBody", parent=styles["BodyLine"], leftIndent=max(indent,0), spaceAfter=1)
            story.append(Paragraph(safe, p_sty))

        # End-of-file flush
        if pending is not None:
            pool = pools.get(pending, [])
            if pool:
                story.append(Paragraph("Evidence:", styles["EvidenceLabel"]))
                g = _image_grid(pool, styles)
                if g: story.append(g)

    else:
        # Fallback: text report missing
        story.append(Paragraph("FINAL VIDEO TRANSACTION SUMMARY", styles["ReportTitle"]))
        story.append(Paragraph(
            f"[Source text report not found at {text_report_path}. Run final_summary.py first.]",
            styles["BodyLine"],
        ))
        for key, label in [("qr","TRANSACTION FLOW OBSERVATION"),
                            ("failed","FAILED TRANSACTION ATTEMPT"),
                            ("executed","TRANSACTION EXECUTION RESULT")]:
            pool = pools.get(key, [])
            if pool:
                story.append(Paragraph(label, styles["SectionHeader"]))
                story.append(Paragraph("Evidence:", styles["EvidenceLabel"]))
                g = _image_grid(pool, styles)
                if g: story.append(g)

    doc = SimpleDocTemplate(
        out_path, pagesize=letter,
        leftMargin=PAGE_MARGIN, rightMargin=PAGE_MARGIN,
        topMargin=PAGE_MARGIN,  bottomMargin=PAGE_MARGIN,
        title="Forensic Video Transaction Evidence Report",
    )
    doc.build(story)
    return out_path


# ── Smoke test ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile, textwrap
    dummy_txt = textwrap.dedent("""\
        FINAL VIDEO TRANSACTION SUMMARY

        BETTING CONTEXT OVERVIEW:
        • Betting-related content detected in 66.7% of segments.
        • Interfaces include wallet views and gameplay navigation.

        TRANSACTION FLOW OBSERVATION:
        • QR codes associated with payment or transfer flows were detected at:
          – 9.07s–10.19s
          – 93.03s–95.25s

        FAILED TRANSACTION ATTEMPT:
        • A transaction attempt was detected but did not complete during 93.03s–95.25s.

        BETTING ATTRIBUTION ANALYSIS:
        • Transaction strongly attributable to betting activity. Confidence: 92.4%.

        OVERALL CONTENT CLASSIFICATION:
        • Betting-related application or informational content.

        FINAL VERDICT:
        • Transaction attempts were observed but did not complete successfully.
    """)
    with tempfile.TemporaryDirectory() as td:
        txt_path = os.path.join(td, "final_summary.txt")
        with open(txt_path, "w") as f: f.write(dummy_txt)
        segs = [
            {"segment_index":1,"start_time":9.07, "end_time":10.19, "proof_frame":None,"frames":[]},
            {"segment_index":2,"start_time":93.03,"end_time":95.25, "proof_frame":None,"frames":[]},
        ]
        out = generate_evidence_report(
            segments=segs, qr_segments=segs, executed_segments=[],
            failed_segments=[segs[1]], likely_segments=segs,
            betting_attribution=[{"decision":"BETTING","confidence":92.4}],
            betting_scores=[50,60], avg_banking=84.0, avg_crypto=0.0,
            meaningful_betting=1, betting_pct=66.7, output_dir=td,
            text_report_path=txt_path,
        )
        print(f"[OK] Smoke test passed -> {out}")
