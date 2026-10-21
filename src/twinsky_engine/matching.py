"""36-point Ashtakoota (Guna Milan): the two natal Moons, in the sidereal zodiac, decide all eight kootas.

The Moon is computed from NASA JPL DE440 with the True Chitra ayanamsa, from the birth's local clock
time in its IANA time zone. Scores follow AstroSage's Guna Milan; ``details`` names each side's
category per koota (in Chinese). Births with an exact time only: a Moon near a nakshatra or sign
boundary can change the score within a day.
"""

from __future__ import annotations

import threading
from typing import Any

import pytz

from . import ephemeris as swe
from .ashtakoota import KUTAS, MAX_TOTAL, METHOD, _details, moon_place, score
from .fetch import default_ephemeris_path
from .schema import BirthInput

FLAGS = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_TRUEPOS | swe.FLG_SPEED
# The ephemeris keeps its path and sidereal mode in module state, like Swiss Ephemeris.
_LOCK = threading.Lock()


def moon_longitude(value: BirthInput, timezone: str, *, ephemeris_path: str | None = None) -> float:
    """The natal Moon's sidereal longitude in degrees (True Chitra ayanamsa)."""
    zone = pytz.timezone(timezone)
    raw = value.raw_datetime
    local = zone.localize(raw, is_dst=None) if raw.tzinfo is None else raw.astimezone(zone)
    utc = local.astimezone(pytz.utc)
    hour = utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1e6) / 3600
    with _LOCK:
        swe.set_ephe_path(str(ephemeris_path or default_ephemeris_path()))
        swe.set_sid_mode(swe.SIDM_TRUE_CITRA)
        position, _ = swe.calc_ut(swe.julday(utc.year, utc.month, utc.day, hour, swe.GREG_CAL), swe.MOON, FLAGS)
    return float(position[0]) % 360


def ashtakoota(groom: BirthInput, bride: BirthInput, *, groom_timezone: str, bride_timezone: str,
               ephemeris_path: str | None = None) -> dict[str, Any]:
    """Eight koota scores out of 36; ``groom`` is the traditional male side, ``bride`` the female side."""
    groom_moon = moon_place(moon_longitude(groom, groom_timezone, ephemeris_path=ephemeris_path))
    bride_moon = moon_place(moon_longitude(bride, bride_timezone, ephemeris_path=ephemeris_path))
    scores = score(groom_moon["longitude"], bride_moon["longitude"])
    return {
        "method": METHOD, "standard": "AstroSage Guna Milan", "groom": groom_moon, "bride": bride_moon,
        "kutas": [{"key": key, "name": name, "max": maximum, "score": scores[key]} for key, name, maximum in KUTAS],
        "total": sum(scores.values()), "max": MAX_TOTAL, "details": _details(groom_moon, bride_moon),
    }
