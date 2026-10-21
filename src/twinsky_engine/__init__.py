"""TwinSky engine: BaZi (Four Pillars) charts, 36-point Ashtakoota matching and a NASA JPL ephemeris.

    from twinsky_engine import birth, bazi_chart, ashtakoota

    me = birth("1994-05-12T09:30", lat=1.29, lng=103.85, gender="female", timezone="Asia/Singapore")
    print(bazi_chart(me).pillars)   # {'year': '甲戌', 'month': '己巳', 'day': '戊戌', 'hour': '丙辰'}

BaZi runs offline. The Moon (for Ashtakoota) needs NASA JPL's DE440 excerpt, about 80 MB, once:
`python -m twinsky_engine.fetch`. ``twinsky_engine.ephemeris`` is a pyswisseph-compatible subset on
Skyfield + DE440 that can be used on its own.
"""

from __future__ import annotations

from datetime import datetime

from . import bazi as _bazi
from .chart_svg import render_bazi_chart, render_bazi_details
from .matching import ashtakoota, moon_longitude
from .schema import BaziChart, BirthInput, SolarTimeMode, TimePrecision, ZiShiRule
from .solar_time import populate_solar_times
from .timezone import resolve_timezone, timezone_offset_hours

__all__ = [
    "BaziChart", "BirthInput", "SolarTimeMode", "TimePrecision", "ZiShiRule",
    "ashtakoota", "bazi_chart", "birth", "moon_longitude", "render_bazi_chart", "render_bazi_details",
]
__version__ = "0.1.0"


def birth(when: str | datetime, *, lat: float, lng: float, gender: str, timezone: str | None = None,
          precision: str = "exact") -> BirthInput:
    """A birth moment in local clock time. The timezone (IANA name) is looked up from the place when omitted.

    ``gender`` is "female" or "male": BaZi luck pillars run forward or backward by it and the year stem.
    BaZi reads true solar time from the longitude; set ``active_mode`` on the result to
    ``SolarTimeMode.STANDARD`` or ``SolarTimeMode.LONGITUDE_EOT`` for the other conventions.
    """
    moment = datetime.fromisoformat(when) if isinstance(when, str) else when
    zone = timezone or resolve_timezone(lat, lng)
    value = BirthInput(raw_datetime=moment, lat=lat, lng=lng, tz_offset=timezone_offset_hours(moment, zone),
                       gender=gender, precision=TimePrecision(precision))
    return populate_solar_times(value)


def bazi_chart(value: BirthInput, *, zishi_rule: str = "no_switch", luck_pillars: int = 8) -> BaziChart:
    """Four pillars, hidden stems, Ten Gods, luck pillars (大运) and annual pillars (流年)."""
    return _bazi.cast(value, ZiShiRule(zishi_rule), dayun_steps=luck_pillars)
