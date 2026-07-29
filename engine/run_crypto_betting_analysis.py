# engine/run_crypto_betting_analysis.py
import os
import json
from engine.transaction_attribution import attribute_transaction


def run_analysis(
    segments,
    segment_verdicts_path="outputs/segment_verdicts.json",
    output_path="outputs/crypto_betting_attribution.json"
):
    """
    Performs final attribution for transactions involving
    betting and/or crypto context.

    This function combines:
    - betting purpose scores
    - crypto support scores
    - transaction execution verdicts
    """

    # -------------------- LOAD REQUIRED DATA --------------------

    # Load per-segment transaction verdicts
    with open(segment_verdicts_path, "r", encoding="utf-8") as f:
        verdicts = json.load(f)

    # Load betting scores computed earlier by betting_classifier
    betting_scores_path = os.path.join(
        os.path.dirname(segment_verdicts_path),
        "betting_segment_scores.json"
    )

    with open(
        betting_scores_path,
        "r",
        encoding="utf-8"
    ) as f:
        betting_scores = json.load(f)

    # Crypto context scores are already present in segment verdicts
    crypto_scores = [s["crypto_context"] for s in verdicts]

    results = []

    # -------------------- ATTRIBUTION LOOP --------------------

    for i, verdict in enumerate(verdicts):

        # Apply formal attribution logic for this segment
        result = attribute_transaction(
            t=i,
            betting_scores=betting_scores,
            crypto_scores=crypto_scores,
            segment_verdict=verdict
        )

        # Store only meaningful attribution outcomes
        if result["decision"] not in ("NO_TRANSACTION", "NOT_BETTING"):
            result["segment_index"] = i + 1
            results.append(result)

    # -------------------- WRITE OUTPUT --------------------

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    return results
