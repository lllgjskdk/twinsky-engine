from bisect import bisect_right
import math
from .constants import NAKSHATRAS


def get_nakshatra(longitude):
    """
    Returns Nakshatra details for a given sidereal longitude (0-360).
    """
    if not math.isfinite(longitude):
        raise ValueError("longitude must be finite")
    longitude = longitude % 360.0
    boundaries = [i * 360.0 / 27 for i in range(28)]
    nak_idx = bisect_right(boundaries, longitude) - 1
    lower, upper = boundaries[nak_idx:nak_idx + 2]
    degree_in_nak = longitude - lower
    fraction = degree_in_nak / (upper - lower)
    pada = bisect_right([lower + (upper - lower) * i / 4 for i in range(5)], longitude)

    nak = NAKSHATRAS[nak_idx]
    return {
        "name": nak["name"],
        "pada": pada,
        "lord": nak["lord"],
        "index": nak_idx,
        "degree_in_nakshatra": degree_in_nak,
        "elapsed_fraction": fraction,
    }
