# engine/crypto_support.py

from typing import List


# -------------------- CONFIGURATION CONSTANTS --------------------

# Minimum crypto score to be considered meaningful
CRYPTO_NOISE_THRESHOLD = 20

# Maximum number of segments to inspect on each side
CRYPTO_MAX_WINDOW = 12

# Stop expansion after this many consecutive low-score segments
CRYPTO_STOP_CONSECUTIVE = 3


# -------------------- HELPER FUNCTIONS --------------------

def distance_weight(i: int, t: int) -> float:
    """
    Distance-based weight function.

    Segments closer to the transaction index `t`
    contribute more than distant segments.
    """
    return 1.0 / (1.0 + abs(i - t))


def expand_crypto_window(
    crypto_scores: List[float],
    t: int
) -> range:
    """
    Expands a window around transaction index `t`
    to capture surrounding crypto-related context.

    Expansion stops when:
    - crypto scores fall below noise threshold
      for several consecutive segments, or
    - maximum window size is exceeded.
    """

    n = len(crypto_scores)

    # Start window from the transaction index
    left = t
    right = t

    # Counters for consecutive low crypto segments
    low_left = 0
    low_right = 0

    # -------- Expand window to the LEFT --------
    i = t - 1
    while i >= 0 and (t - i) <= CRYPTO_MAX_WINDOW:

        if crypto_scores[i] < CRYPTO_NOISE_THRESHOLD:
            low_left += 1
            if low_left >= CRYPTO_STOP_CONSECUTIVE:
                break
        else:
            # Reset counter if meaningful crypto context appears
            low_left = 0

        left = i
        i -= 1

    # -------- Expand window to the RIGHT --------
    i = t + 1
    while i < n and (i - t) <= CRYPTO_MAX_WINDOW:

        if crypto_scores[i] < CRYPTO_NOISE_THRESHOLD:
            low_right += 1
            if low_right >= CRYPTO_STOP_CONSECUTIVE:
                break
        else:
            # Reset counter if meaningful crypto context appears
            low_right = 0

        right = i
        i += 1

    # Return the final continuous index range
    return range(left, right + 1)


def compute_crypto_support(
    crypto_scores: List[float],
    t: int
) -> float:
    """
    Computes crypto support score for a transaction at index `t`.

    Formula:
        CryptoSupport(T) =
            Σ(crypto_score_i × distance_weight) / Σ(distance_weight)
    """

    window = expand_crypto_window(crypto_scores, t)

    weighted_sum = 0.0
    weight_total = 0.0

    # Apply distance-weighted averaging
    for i in window:
        w = distance_weight(i, t)
        weighted_sum += crypto_scores[i] * w
        weight_total += w

    # Safety check to avoid division by zero
    if weight_total == 0:
        return 0.0

    return round(weighted_sum / weight_total, 2)
