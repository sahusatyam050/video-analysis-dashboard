# engine/transaction_attribution.py

from typing import Dict
from engine.crypto_support import compute_crypto_support
from engine.betting_purpose import compute_betting_purpose


def attribute_transaction(
    t: int,
    betting_scores,
    crypto_scores,
    segment_verdict: Dict
) -> Dict:
    """
    Determines what a detected transaction should be attributed to.

    Possible outcomes:
    - BETTING
    - BETTING_CRYPTO_ASSISTED
    - BETTING_INFORMATIONAL
    - CRYPTO_ONLY
    - FAILED_TRANSACTION
    - NOT_BETTING
    - NO_TRANSACTION
    """

    # Extract execution and likelihood scores from segment verdict
    E = segment_verdict["transaction_executed"]
    L = segment_verdict["transaction_likely"]
    failed = segment_verdict.get("transactionFailed", False)

    # -------------------- GATE 1: TRANSACTION VALIDITY --------------------

    # If the segment does not show execution or at least a likely flow
    # (QR-assisted initiation), ignore it completely
    if not (E >= 70 or (L >= 60 and segment_verdict.get("qr_detected"))):
        return {"decision": "NO_TRANSACTION"}

    # Explicit failure signals always override everything
    if failed:
        return {"decision": "FAILED_TRANSACTION"}

    # -------------------- CONTEXT SUPPORT COMPUTATION --------------------

    # Compute how strongly surrounding segments indicate betting intent
    betting_purpose = compute_betting_purpose(betting_scores, t)

    # Compute how strongly crypto context supports the transaction
    crypto_support = compute_crypto_support(crypto_scores, t)

    # -------------------- GATE 2: BETTING PRESENCE --------------------

    # If betting context is weak, check if crypto dominates instead
    if betting_purpose < 20:
        if crypto_support >= 60:
            return {
                "decision": "CRYPTO_ONLY",
                "betting_purpose": betting_purpose,
                "crypto_support": crypto_support
            }

        # No meaningful betting or crypto attribution
        return {"decision": "NOT_BETTING"}

    # -------------------- CASE A: DEFINITIVE BETTING --------------------

    # Strong betting intent + confirmed execution
    if betting_purpose >= 40 and E >= 70:
        return {
            "decision": "BETTING",
            "confidence": min(95, betting_purpose + 5),
            "betting_purpose": betting_purpose,
            "crypto_support": crypto_support
        }

    # -------------------- CASE B: CRYPTO-ASSISTED BETTING --------------------

    # Moderate betting intent but strong crypto backing
    if 40 <= betting_purpose < 60 and crypto_support >= 60 and E >= 70:
        return {
            "decision": "BETTING_CRYPTO_ASSISTED",
            "confidence": 70 + (crypto_support - 60) * 0.3,
            "betting_purpose": betting_purpose,
            "crypto_support": crypto_support
        }

    # -------------------- CASE C: INFORMATIONAL BETTING --------------------

    # Strong betting UI context without transaction execution
    if betting_purpose >= 60 and E < 70 and L < 60:
        return {
            "decision": "BETTING_INFORMATIONAL",
            "betting_purpose": betting_purpose
        }

    # -------------------- CASE D: AMBIGUOUS --------------------

    # Borderline betting signals that cannot be confidently classified
    if 20 <= betting_purpose < 40:
        return {
            "decision": "AMBIGUOUS",
            "confidence": 45,
            "betting_purpose": betting_purpose,
            "crypto_support": crypto_support
        }

    # Default fallback
    return {"decision": "NOT_BETTING"}
