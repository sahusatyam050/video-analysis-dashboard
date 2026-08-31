import json
import re
import math
from difflib import SequenceMatcher
from collections import defaultdict


# -------------------- PRE-COMPILED REGEX PATTERNS --------------------
# Compiled once at module load — avoids recompilation on every segment call

_ODDS_PATTERN_CACHE = {}

def _get_odds_pattern(regex_str):
    """Caches compiled odds regex to avoid recompilation."""
    if regex_str not in _ODDS_PATTERN_CACHE:
        _ODDS_PATTERN_CACHE[regex_str] = re.compile(regex_str)
    return _ODDS_PATTERN_CACHE[regex_str]


# -------------------- BASIC UTILITY FUNCTIONS --------------------

def normalize(text):
    """
    Converts text to lowercase so matching becomes case-insensitive.
    OCR text can be noisy, so this is the safest baseline.
    """
    return text.lower() if text else ""


def fuzzy_match(a, b):
    """
    Computes fuzzy similarity between two strings using SequenceMatcher.
    Returns a percentage score between 0 and 100.
    Used to tolerate OCR spelling errors.
    """
    return SequenceMatcher(None, a, b).ratio() * 100


def soft_saturate(x, scale=35.0):
    """
    Converts a raw accumulated score into a smooth percentage.
    Prevents very large raw scores from exploding the final result.
    """
    return 100 * (1 - math.exp(-x / scale))


# -------------------- BETTING SIGNAL DETECTION --------------------

def detect_brands(text, brand_rules):
    """
    Detects betting platform names like Dream11, Stake, 1xBet, etc.
    These are strong indicators of betting intent.
    """
    score = 0
    hits = []

    for rule in brand_rules:
        if rule["term"] in text:
            score += rule["weight"]
            hits.append(rule["term"])

    return score, hits


def detect_phrases(text, phrase_rules):
    score = 0
    hits = []

    text = text.lower()

    for rule in phrase_rules:
        phrase = rule["phrase"].lower()

        if phrase in text:
            score += rule["weight"]
            hits.append(phrase)

    return score, hits

def detect_odds(text, odds_rules):

    pattern = _get_odds_pattern(
        odds_rules["decimal_odds_regex"]
    )

    matches = pattern.findall(text)

    # Sportsbook-related context words
    betting_context_words = [
        "odds",
        "market",
        "markets",
        "bet",
        "bets",
        "sports",
        "football",
        "cricket",
        "tennis",
        "basketball",
        "over",
        "under",
        "handicap"
    ]

    context_hits = sum(
        1 for word in betting_context_words
        if word in text
    )

    # Keep only realistic betting odds
    valid_odds = []

    for m in matches:
        try:
            value = float(m)

            if 1.01 <= value <= 20:
                valid_odds.append(value)

        except ValueError:
            pass

    # Strong sportsbook signal
    if len(valid_odds) >= 4 and context_hits >= 1:
        return odds_rules["weight"] + 25, valid_odds

    # Medium sportsbook signal
    if len(valid_odds) >= 2 and context_hits >= 2:
        return odds_rules["weight"], valid_odds

    return 0, []


def is_instructional(text, suppressors):
    """
    Suppresses educational or tutorial content.
    Prevents false positives from demo or how-to videos.
    """
    return any(s in text for s in suppressors)


# -------------------- CORE BETTING CLASSIFIER --------------------

def compute_betting_context(segment, rules):
    """
    Computes betting relevance score for a single segment.
    Uses weighted signals defined in bettingSignals.json.
    Expects segment["ocr_text"] to already be normalized (lowercase).
    """

    # ocr_text is already normalized by extractframes.py — no re-normalize needed
    text = segment.get("ocr_text", "").lower()

    # Instructional content should not be treated as betting
    if is_instructional(text, rules["suppressors"]["instructional"]):
        return 0, {"suppressed": True}

    breakdown = {}
    total = 0

    # ---- Brand detection (strongest signal) ----
    s, hits = detect_brands(text, rules["brand_rules"])
    total += s
    breakdown["brands"] = hits

    # ---- Betting action phrases ----
    s, hits = detect_phrases(text, rules["betting_phrases"])
    total += s
    breakdown["betting_phrases"] = hits

    # ---- Wallet and balance related phrases ----
    s, hits = detect_phrases(text, rules["wallet_phrases"])
    total += s
    breakdown["wallet_phrases"] = hits

    # ---- Fantasy sports UI elements ----
    s, hits = detect_phrases(text, rules["fantasy_ui_phrases"])
    total += s
    breakdown["fantasy_ui"] = hits

    # ---- Casino-style betting phrases ----
    s, hits = detect_phrases(text, rules["casino_phrases"])
    total += s
    breakdown["casino"] = hits
    # ---- Sportsbook UI phrases ----
    s, hits = detect_phrases(
        text,
        rules.get("sportsbook_ui_phrases", [])
    )
    total += s
    breakdown["sportsbook_ui"] = hits

    # ---- Promotional betting language ----
    s, hits = detect_phrases(text, rules["promo_phrases"])
    total += s
    breakdown["promo"] = hits

    # ---- Betting odds detection ----
    s, hits = detect_odds(text, rules["odds_rules"])
    total += s
    breakdown["odds"] = hits

    # Convert raw score into bounded percentage
    score = min(100, round(soft_saturate(total), 1))

    breakdown["raw_score"] = total
    breakdown["final_score"] = score

    return score, breakdown


# -------------------- TEMPORAL ATTRIBUTION LOGIC --------------------

def attribute_transactions(segments, segment_verdicts, rules):
    """
    Attributes betting purpose to executed or likely transactions
    by looking at surrounding betting context across segments.
    """

    betting_scores = []
    explanations = []

    # Step 1: Compute betting score for each segment
    for seg in segments:
        score, expl = compute_betting_context(seg, rules)
        betting_scores.append(score)
        explanations.append(expl)
    # -------------------- TEMPORAL SMOOTHING --------------------
    # -------------------------------------------------
    # Betting context persistence
    # -------------------------------------------------

    context_boost_remaining = 0

    for i in range(len(betting_scores)):

        if betting_scores[i] >= 70:
            context_boost_remaining = 10

        elif context_boost_remaining > 0:
            betting_scores[i] = min(
                100,
                betting_scores[i] + 15
            )
            context_boost_remaining -= 1

    smoothed_scores = betting_scores.copy()

    for i in range(1, len(betting_scores) - 1):

        prev_score = betting_scores[i - 1]
        curr_score = betting_scores[i]
        next_score = betting_scores[i + 1]

        smoothed_scores[i] = round(
            0.25 * prev_score +
            0.50 * curr_score +
            0.25 * next_score,
            1
        )

    # OCR miss recovery
    for i in range(1, len(smoothed_scores) - 1):

        if (
            smoothed_scores[i] < 40 and
            smoothed_scores[i - 1] >= 50 and
            smoothed_scores[i + 1] >= 50
        ):
            smoothed_scores[i] = 40

    betting_scores = smoothed_scores

    results = []

    # Step 2: Attribute betting purpose to transactions
    for i, verdict in enumerate(segment_verdicts):

        if verdict["transaction_executed"] >= 70 or verdict["transaction_likely"] >= 60:
            weighted_sum = 0
            weight_total = 0

            # Look at surrounding segments with distance-based weighting
            for j in range(len(betting_scores)):
                dist = abs(i - j)

                if dist > 12:
                    continue

                w = 1 / (1 + dist)
                weighted_sum += betting_scores[j] * w
                weight_total += w

            purpose_score = weighted_sum / weight_total if weight_total else 0
            used_for_betting = purpose_score >= 35

            results.append({
                "segment_index": i + 1,
                "transaction_time": f"{verdict['start_time']}–{verdict['end_time']}",
                "betting_purpose_score": round(purpose_score, 1),
                "transaction_used_for_betting": used_for_betting,
                "confidence": min(98, round(purpose_score + 10, 1)),
                "evidence": explanations[i]
            })

    return betting_scores, results, explanations


# -------------------- ENTRY POINT --------------------

def run_betting_analysis(
    segments,
    segment_verdicts_path="outputs/segment_verdicts.json",
    rules_path="rules/bettingSignals.json",
    output_dir="outputs"
):
    """
    Main entry function for betting analysis.
    Loads rules and segment verdicts, runs attribution,
    and writes outputs to disk.
    """

    with open(segment_verdicts_path, "r", encoding="utf-8") as f:
        verdicts = json.load(f)

    with open(rules_path, "r", encoding="utf-8") as f:
        rules = json.load(f)

    scores, attributions, explanations = attribute_transactions(
        segments, verdicts, rules
    )

    with open(
        f"{output_dir}/betting_segment_scores.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(scores, f, indent=2)

    with open(
        f"{output_dir}/betting_transaction_attribution.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(attributions, f, indent=2)

    with open(
        f"{output_dir}/betting_segment_evidence.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(explanations, f, indent=2)

    return attributions
