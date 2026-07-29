import json
import os

from engine.generate_evidence_report import generate_evidence_report


# ============================================================
# Utility loaders
# ============================================================

def load_segment_verdicts(path="outputs/segment_verdicts.json"):
    """
    Loads the per-segment verdicts generated during scoring.
    This acts as the primary input for the evidence report.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def time_range(seg):
    """
    Formats the start and end time of a segment
    into a readable string (kept for callers that still need plain text).
    """
    return f"{seg['start_time']:.2f}s\u2013{seg['end_time']:.2f}s"


def safe_load(path, default):
    """
    Safely loads a JSON file if it exists.
    If the file is missing, returns a default value.
    """
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


# ============================================================
# Final summary generation
# ============================================================

def generate_final_summary(segments, output_dir="outputs", video_name=None):
    """
    Classifies every segment into the signal buckets used downstream
    (QR/transaction flow, executed, failed, likely, betting/crypto
    averages) and hands them off to generate_evidence_report() to
    render the forensic PDF (evidence_report.pdf). No text report is
    written anymore.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Load betting-related outputs if they exist
    betting_scores = safe_load(
        os.path.join(output_dir, "betting_segment_scores.json"), []
    )

    betting_attribution = safe_load(
        os.path.join(output_dir, "betting_transaction_attribution.json"), []
    )

    # -------------------- COLLECT SIGNALS --------------------

    qr_segments = []
    executed_segments = []
    failed_segments = []
    likely_segments = []

    banking_scores = []
    crypto_scores = []

    # Iterate over all segments to classify them
    for s in segments:
        banking_scores.append(s["banking_context"])
        crypto_scores.append(s["crypto_context"])

        if s["qr_detected"]:
            qr_segments.append(s)

        if s["transaction_likely"] >= 60:
            likely_segments.append(s)

        if s["transaction_failed"]:
            failed_segments.append(s)

        if s["transaction_executed"] >= 95:
            executed_segments.append(s)

    # Compute average context strength across the video
    avg_banking = sum(banking_scores) / len(banking_scores) if banking_scores else 0
    avg_crypto = sum(crypto_scores) / len(crypto_scores) if crypto_scores else 0

    meaningful_betting = sum(1 for b in betting_scores if b >= 40)
    betting_pct = (meaningful_betting / len(segments) * 100) if segments else 0

    # -------------------- BUILD PDF EVIDENCE REPORT --------------------

    output_path = generate_evidence_report(
        segments=segments,
        qr_segments=qr_segments,
        executed_segments=executed_segments,
        failed_segments=failed_segments,
        likely_segments=likely_segments,
        betting_attribution=betting_attribution,
        betting_scores=betting_scores,
        avg_banking=avg_banking,
        avg_crypto=avg_crypto,
        meaningful_betting=meaningful_betting,
        betting_pct=betting_pct,
        output_dir=output_dir,
        video_name=video_name,
    )

    return output_path


# ============================================================
# Standalone execution support
# ============================================================

if __name__ == "__main__":
    segments = load_segment_verdicts()
    out = generate_final_summary(segments)
    print(f"[OK] Evidence report written to {out}")
