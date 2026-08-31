import re
import json
import os
from collections import Counter
from difflib import SequenceMatcher


# -------------------- PRE-COMPILED REGEX PATTERNS --------------------
# Compiled once at module load — avoids recompilation on every segment call

AMOUNT_PATTERN = re.compile(r"(₹|\$|€|£)\s?\d+(?:[,]\d+)*(?:\.\d+)?")


# ============================================================
# Helper utility functions
# These are small reusable functions used across the file
# ============================================================

def count_hits(text, terms):
    """
    Counts how many predefined terms appear in the given text.
    Used to measure signal strength for banking, crypto, etc.
    """
    hits = []
    for t in terms:
        if t in text:
            hits.append(t)
    return hits


def soft_saturate(hits, base=0.88):
    """
    Converts raw hit count into a smoothly increasing value.
    Prevents score from jumping too fast when hits increase.
    """
    return 1 - pow(base, hits)


def fuzzy_ratio(a, b):
    """
    Computes similarity between two strings using fuzzy matching.
    Returns a percentage (0–100).
    """
    return int(SequenceMatcher(None, a, b).ratio() * 100)


def pick_middle_frames(frame_texts, k=8):
    """
    Picks OCR text from the middle frames of a segment.
    This avoids transition frames and focuses on stable UI state.
    """
    if not frame_texts:
        return []

    n = len(frame_texts)

    if n <= k:
        return frame_texts

    mid = n // 2
    half = k // 2

    start = max(0, mid - half)
    end = min(n, mid + half)

    return frame_texts[start:end]


def extract_phrases(text, min_len=2, max_len=5):
    """
    Extracts word phrases of length 2 to 5 from text.
    Useful for detecting structured phrases instead of single words.
    """
    tokens = text.split()
    phrases = []

    for i in range(len(tokens)):
        for j in range(i + min_len, min(i + max_len + 1, len(tokens) + 1)):
            phrases.append(" ".join(tokens[i:j]))

    return phrases


# ============================================================
# Context confidence scoring
# Used for banking and crypto classification
# ============================================================

def compute_context_confidence(text, terms, cap=88.0, context_type="generic"):
    """
    Computes confidence score for a specific context
    (banking / crypto) based on keyword density and diversity.
    """
    if not text:
        return 0.0, []

    hits = [t for t in terms if t in text]
    total_hits = len(hits)

    if total_hits == 0:
        return 0.0, []

    diversity = len(set(hits))
    base = 1 - pow(0.88, total_hits)
    diversity_factor = min(1.0, diversity / 6)

    score = 100 * base * (0.7 + 0.3 * diversity_factor)

    # Small boost when few but strong signals are present
    if total_hits <= 3:
        if context_type == "banking":
            score += 18 + (diversity * 4)
        elif context_type == "crypto":
            score += 8 + (diversity * 2)

    # Extra boost for strong dense contexts
    if total_hits >= 6 and diversity >= 4:
        score += 8
    if total_hits >= 10 and diversity >= 6:
        score += 12

    return round(min(score, cap), 1), list(set(hits))


# ============================================================
# Transaction likelihood estimation
# ============================================================

def compute_transaction_likelihood(text, roles, qr_texts=None):
    """
    Estimates how likely a transaction flow is present
    without confirming execution.
    """
    signals = 0

    if count_hits(text, roles["user_action"]):
        signals += 1
    if count_hits(text, roles["payment_interface"]):
        signals += 1
    if count_hits(text, roles["progression"]):
        signals += 1
    if AMOUNT_PATTERN.search(text):
        signals += 1

    # QR codes add strong evidence for transaction flow
    if qr_texts:
        for qr in qr_texts:
            qr = qr.lower()
            if qr.startswith("upi://"):
                signals += 2
            elif "pay" in qr or "payment" in qr:
                signals += 1.5

    # Post-payment density boost
    has_amount = bool(AMOUNT_PATTERN.search(text))
    has_reference = count_hits(text, roles["proof"])
    has_financial_ctx = count_hits(text, roles["financial_context"])

    if has_amount and has_reference and has_financial_ctx:
        signals += 2

    if signals == 0:
        return 0.0

    return round(min(85.0, signals * 18.0), 1)


def compute_transaction_execution(text, roles):
    """
    Confirms transaction execution only if
    proof + completion + amount are present together.
    """
    proof = count_hits(text, roles["proof"])
    completion = count_hits(text, roles["completion"])
    amount = AMOUNT_PATTERN.search(text)

    if proof and completion and amount:
        return 100.0

    return 0.0


def is_future_execution_context(text, sentence_rules):
    """
    Detects sentences that describe future or hypothetical execution.
    """
    for s in sentence_rules.get("execution_future_suppressor", []):
        if s in text:
            return True
    return False


# ============================================================
# Execution and suppression logic
# ============================================================

def is_execution_failure(text, sentence_rules):
    """
    Detects explicit transaction failure messages.
    """
    text = text.lower()
    for s in sentence_rules.get("execution_failure_suppressor", []):
        if s in text:
            return True
    return False


def hard_execution_banner(text, sentence_rules):
    """
    Confirms transaction execution using strict sentence logic.
    """
    text = text.lower()

    # Block instructional or future-oriented screens
    if is_payment_instruction_page(text, sentence_rules):
        return False
    if is_future_execution_context(text, sentence_rules):
        return False

    # Failure always overrides execution
    if is_execution_failure(text, sentence_rules):
        return False

    threshold = sentence_rules.get("fuzzy_threshold", 80)
    tokens = text.split()

    # Sentence-based execution confirmation
    for s in sentence_rules.get("transaction_executed_sentences", []):
        s_len = len(s.split())
        for i in range(len(tokens)):
            window = " ".join(tokens[i:i + s_len + 2])
            if fuzzy_ratio(window, s) >= threshold:
                return True

    # Pattern-based execution confirmation
    for p in sentence_rules.get("transaction_execution_patterns", []):
        verbs = p.get("verbs", [])
        entities = p.get("entities", [])

        for i in range(len(tokens)):
            window = " ".join(tokens[i:i + 4])
            verb_hit = any(fuzzy_ratio(window, v) >= threshold for v in verbs)
            entity_hit = any(fuzzy_ratio(window, e) >= threshold for e in entities)

            if verb_hit and entity_hit:
                return True

    return False


def is_payment_instruction_page(text, sentence_rules):
    """
    Detects payment instruction or redirection screens.
    """
    text = text.lower()
    tokens = text.split()

    phrases = sentence_rules.get("payment_instruction_phrases", [])

    for p in phrases:
        p_len = len(p.split())
        for i in range(len(tokens)):
            window = " ".join(tokens[i:i + p_len + 2])
            if p in window:
                return True

    return False


def commerce_suppressor_gate(text, sentence_rules, roles):
    """
    Suppresses execution detection on commerce-heavy pages.
    """
    text = text.lower()

    commerce_terms = roles.get("commerce_suppressor", [])
    executed_sentences = sentence_rules.get("transaction_executed_sentences", [])
    threshold = sentence_rules.get("fuzzy_threshold", 80)

    # If a real execution sentence exists, never suppress
    for s in executed_sentences:
        if s in text:
            return False

    commerce_hits = 0

    for term in commerce_terms:
        if len(term.split()) < 2:
            continue

        if term in text or fuzzy_ratio(text, term) >= threshold:
            commerce_hits += 1

    return commerce_hits >= 2


def apply_sentence_logic(base_likely, base_exec, frame_texts, sentence_rules, roles):
    """
    Applies sentence-level execution logic on stable frames only.
    """
    likely = base_likely
    executed = base_exec

    texts = pick_middle_frames(frame_texts)

    # Failure blocks execution immediately
    for t in texts:
        if is_execution_failure(t, sentence_rules):
            return base_likely, 0.0

    threshold = sentence_rules.get("fuzzy_threshold", 80)

    # Hard execution confirmation
    for t in texts:
        if hard_execution_banner(t, sentence_rules):
            if not commerce_suppressor_gate(t, sentence_rules, roles):
                return likely, 95.0

    # Soft likelihood boost
    for t in texts:
        for s in sentence_rules.get("transaction_likely_sentences", []):
            if fuzzy_ratio(t, s) >= threshold:
                likely = max(likely, 60.0)

    return likely, 0.0


# ============================================================
# Output writing
# ============================================================

def write_segment_verdicts(segments, segment_scores, output_dir="outputs"):
    """
    Writes per-segment verdicts into JSON file.
    """
    os.makedirs(output_dir, exist_ok=True)

    data = []

    for idx, (seg, score) in enumerate(zip(segments, segment_scores), start=1):
        data.append({
            "segment_index": idx,
            "start_time": seg.get("startTime"),
            "end_time": seg.get("endTime"),
            "qr_detected": bool(seg.get("qrTexts")),
            "banking_context": score["bankingContextPercentage"],
            "banking_hits": score.get("bankingHits", []),
            "crypto_context": score["cryptoContextPercentage"],
            "crypto_hits": score.get("cryptoHits", []),
            "transaction_likely": score["transactionLikelyPercentage"],
            "transaction_executed": score["transactionExecutedPercentage"],
            "transaction_failed": score.get("transactionFailed", False),
            "proof_frame": seg.get("proof_frame")
        })

    path = os.path.join(output_dir, "segment_verdicts.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return path


# ============================================================
# Main scoring entry point
# ============================================================

def score_segment(segment, rules):
    """
    Computes all scores for a single segment.
    """
    text = segment.get("ocr_text", "")
    frame_texts = segment.get("frame_texts", [])
    qr_texts = segment.get("qrTexts", [])
    roles = rules["roles"]
    sentence_rules = rules.get("sentence_logic", {})

    # QR-based fast path
    for qr in qr_texts:
        if qr.lower().startswith("upi://"):
            b_conf, b_hits = compute_context_confidence(
                text, roles["financial_context"], cap=88.0, context_type="banking"
            )
            c_conf, c_hits = compute_context_confidence(
                text, roles["crypto_context"], cap=85.0, context_type="crypto"
            )
            return {
                "bankingContextPercentage": b_conf,
                "bankingHits": b_hits,
                "cryptoContextPercentage": c_conf,
                "cryptoHits": c_hits,
                "transactionLikelyPercentage": compute_transaction_likelihood(
                    text, roles, qr_texts
                ),
                "transactionExecutedPercentage": 0.0,
                "categorized_hits": segment.get("categorized_hits", {})
            }

    banking_conf, banking_hits = compute_context_confidence(
        text, roles["financial_context"], cap=88.0, context_type="banking"
    )

    crypto_conf, crypto_hits = compute_context_confidence(
        text, roles["crypto_context"], cap=85.0, context_type="crypto"
    )

    transaction_likely = compute_transaction_likelihood(
        text, roles, qr_texts
    )

    transaction_likely, transaction_executed = apply_sentence_logic(
        transaction_likely, 0.0, frame_texts, sentence_rules, roles
    )

    failure_detected = is_execution_failure(text, sentence_rules)

    return {
        "bankingContextPercentage": banking_conf,
        "bankingHits": banking_hits,
        "cryptoContextPercentage": crypto_conf,
        "cryptoHits": crypto_hits,
        "transactionLikelyPercentage": transaction_likely,
        "transactionExecutedPercentage": transaction_executed,
        "transactionFailed": failure_detected,
        "categorized_hits": segment.get("categorized_hits", {})
    }
