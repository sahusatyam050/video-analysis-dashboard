# engine/betting_purpose.py

from typing import List


# -------------------- CONFIGURATION CONSTANTS --------------------

# Minimum betting score to be considered meaningful
BETTING_NOISE_THRESHOLD = 15

# Maximum number of segments to look left and right
BETTING_MAX_WINDOW = 12

# Number of consecutive low-score segments after which expansion stops
BETTING_STOP_CONSECUTIVE = 3


# -------------------- HELPER FUNCTIONS --------------------

def distance_weight(i: int, t: int) -> float:
    """
    Computes distance-based weight.
    Segments closer to the transaction index have higher influence.
    """
    return 1.0 / (1.0 + abs(i - t))


def expand_betting_window(
    betting_scores: List[float],
    t: int
) -> range:
    """
    Expands a window around transaction index `t`
    to include nearby segments that contain betting context.

    Expansion stops when:
    - too many consecutive low-betting segments are found, or
    - maximum window size is exceeded.
    """

    n = len(betting_scores)

    # Start window at the transaction index itself
    left = t
    right = t

    # Counters for consecutive low-score segments
    low_left = 0
    low_right = 0

    # -------- Expand window to the LEFT --------
    i = t - 1
    while i >= 0 and (t - i) <= BETTING_MAX_WINDOW:

        if betting_scores[i] < BETTING_NOISE_THRESHOLD:
            low_left += 1
            if low_left >= BETTING_STOP_CONSECUTIVE:
                break
        else:
            # Reset if meaningful betting context is found
            low_left = 0

        left = i
        i -= 1

    # -------- Expand window to the RIGHT --------
    i = t + 1
    while i < n and (i - t) <= BETTING_MAX_WINDOW:

        if betting_scores[i] < BETTING_NOISE_THRESHOLD:
            low_right += 1
            if low_right >= BETTING_STOP_CONSECUTIVE:
                break
        else:
            # Reset if meaningful betting context is found
            low_right = 0

        right = i
        i += 1

    # Return the final continuous window
    return range(left, right + 1)


def compute_betting_purpose(
    betting_scores: List[float],
    t: int
) -> float:
    """
    Computes the betting purpose score for a transaction at index `t`.

    Uses:
    - expanded betting window
    - distance-based weighted averaging
    """

    window = expand_betting_window(betting_scores, t)

    weighted_sum = 0.0
    weight_total = 0.0

    # Apply distance-weighted averaging
    for i in window:
        w = distance_weight(i, t)
        weighted_sum += betting_scores[i] * w
        weight_total += w

    # Safety check to avoid division by zero
    if weight_total == 0:
        return 0.0

    return round(weighted_sum / weight_total, 2)
