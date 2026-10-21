"""Planetary positions for the chart engine: Skyfield with NASA JPL DE440.

Implements the part of the pyswisseph interface the engine calls (same names, flag
values, return shapes and exceptions), so vendor/dashaflow keeps its call sites.
The conventions reproduce what the engine received from Swiss Ephemeris 2.10.03;
the TwinSky app's research note measures the agreement.

Inputs are MIT-licensed code (Skyfield, jplephem) and public data: JPL DE440, the
ΔT table in data/ephemeris/delta_t.json (USNO/IERS observations and published
models), the Hipparcos position of Spica and the Indian Astronomical Ephemeris
definition of the Lahiri ayanamsa.

State (ephemeris path, sidereal mode, observer) is module-global like Swiss
Ephemeris; callers serialise through twinsky_engine._vendor.dashaflow.swiss_state.SWISS_LOCK.
`calc_ut_many` is an addition for callers that need many instants at once.
"""

from __future__ import annotations

import json
import math
import operator
from collections import OrderedDict
from functools import lru_cache
from pathlib import Path

import numpy as np
import skyfield
from skyfield.api import Star, load_file, wgs84
from skyfield.framelib import ICRS_to_J2000
from skyfield.functions import mxm, mxv, rot_x, rot_y, rot_z
from skyfield.iokit import Loader
from skyfield.precessionlib import compute_precession
from skyfield.timelib import Timescale

# Flag and body numbers as pyswisseph defines them; saved profiles record them.
FLG_JPLEPH, FLG_SWIEPH, FLG_MOSEPH = 1, 2, 4
FLG_TRUEPOS, FLG_NONUT, FLG_SPEED = 16, 64, 256
FLG_NOGDEFL, FLG_NOABERR, FLG_EQUATORIAL, FLG_SIDEREAL = 512, 1024, 2048, 65536
SUN, MOON, MERCURY, VENUS, MARS, JUPITER, SATURN = 0, 1, 2, 3, 4, 5, 6
MEAN_NODE, TRUE_NODE, ECL_NUT = 10, 11, -1
SIDM_LAHIRI, SIDM_TRUE_CITRA = 1, 27
JUL_CAL, GREG_CAL = 0, 1
CALC_RISE, CALC_SET = 1, 2
BIT_DISC_CENTER, BIT_NO_REFRACTION = 256, 512

EPHEMERIS_FILE = "de440_1760_2560.bsp"
DELTA_T_FILE = Path(__file__).resolve().parent / "data" / "delta_t.json"
EPHEMERIS_MASK = FLG_JPLEPH | FLG_SWIEPH | FLG_MOSEPH


class Error(Exception):
    """Raised where pyswisseph raises swisseph.Error."""


_DEG = math.pi / 180.0
_ASEC = _DEG / 3600.0
_state = {"ephe_path": None, "sid_mode": SIDM_LAHIRI}


# ---- ΔT ----------------------------------------------------------------------------------
def _jan1(year):
    """Julian Day of 1 January 0h UT, proleptic Gregorian (Meeus ch. 7); arrays allowed."""
    y = np.asarray(year, dtype=np.int64) - 1
    a = y // 100
    return np.floor(365.25 * (y + 4716)) + np.floor(30.6001 * 14) + 1 + 2 - a + a // 4 - 1524.5


def _year_and_fraction(jd_ut):
    jd = np.asarray(jd_ut, dtype=float)
    year = np.floor(2000.0 + (jd - 2451545.0) / 365.2425).astype(np.int64)
    year = np.where(jd < _jan1(year), year - 1, year)
    year = np.where(jd >= _jan1(year + 1), year + 1, year)
    start = _jan1(year)
    return year, (jd - start) / (_jan1(year + 1) - start)


def _bessel(values, first_year, year, p):
    """Bessel's interpolation to fourth differences over 1 January knots."""
    i = year - first_year
    if np.any(i < 2) or np.any(i + 3 >= len(values)):
        raise Error("ΔT requested outside the tabulated years")
    fm2, fm1, f0, f1, f2, f3 = (values[i + k] for k in (-2, -1, 0, 1, 2, 3))
    d2m, d2p = fm1 - 2 * f0 + f1, f0 - 2 * f1 + f2
    d4m = fm2 - 4 * fm1 + 6 * f0 - 4 * f1 + f2
    d4p = fm1 - 4 * f0 + 6 * f1 - 4 * f2 + f3
    return (f0 + p * (f1 - f0) + p * (p - 1) / 4 * (d2m + d2p)
            + p * (p - 0.5) * (p - 1) / 6 * (d2p - d2m)
            + (p + 1) * p * (p - 1) * (p - 2) / 48 * (d4m + d4p))


@lru_cache(maxsize=1)
def _delta_t_table():
    data = json.loads(DELTA_T_FILE.read_text(encoding="utf-8"))

    def series(block):
        years = sorted(int(y) for y in block)
        if years != list(range(years[0], years[-1] + 1)):
            raise Error("ΔT table has gaps")
        return years[0], np.array([block[str(y)] for y in years], dtype=float)

    return {"version": data["version"], "model": series(data["model"]), "table": series(data["table"]),
            "start": int(data["table_start_year"]), "blend": float(data["blend_days_before_table"])}


def delta_t_seconds(jd_ut):
    """ΔT = TT − UT1 in seconds as a function of UT; scalar or array."""
    tab = _delta_t_table()
    jd = np.asarray(jd_ut, dtype=float)
    year, p = _year_and_fraction(jd)
    start_jd = float(_jan1(tab["start"]))
    late = jd >= start_jd
    out = np.empty_like(jd)
    if np.any(late):
        out[late] = _bessel(tab["table"][1], tab["table"][0], year[late], p[late])
    if np.any(~late):
        early = ~late
        model = _bessel(tab["model"][1], tab["model"][0], year[early], p[early])
        start_year = np.full(1, tab["start"])
        step = (_bessel(tab["table"][1], tab["table"][0], start_year, np.zeros(1))
                - _bessel(tab["model"][1], tab["model"][0], start_year, np.zeros(1)))[0]
        ramp = np.clip(1.0 - (start_jd - jd[early]) / tab["blend"], 0.0, 1.0)
        out[early] = model + ramp * step
    return out if out.ndim else float(out)


def _delta_t_of_tt(tt):
    ut = np.asarray(tt, dtype=float) - delta_t_seconds(tt) / 86400.0
    ut = np.asarray(tt, dtype=float) - delta_t_seconds(ut) / 86400.0
    return delta_t_seconds(ut)


@lru_cache(maxsize=1)
def _timescale():
    builtin = Loader(str(DELTA_T_FILE.parent)).timescale(builtin=True)
    return Timescale(_delta_t_of_tt, builtin.leap_dates, builtin.leap_offsets)


def _time(jd_ut):
    """A Skyfield Time whose TT is UT + ΔT(UT), as Swiss Ephemeris defines it."""
    jd = np.asarray(jd_ut, dtype=float)
    return _timescale().tt_jd(jd + delta_t_seconds(jd) / 86400.0)


def deltat(jd_ut):
    return float(delta_t_seconds(float(jd_ut))) / 86400.0


# ---- ephemeris ---------------------------------------------------------------------------
@lru_cache(maxsize=4)
def _kernel(path):
    file = Path(path) / EPHEMERIS_FILE
    if not file.is_file():
        raise Error(f"JPL ephemeris {EPHEMERIS_FILE} not found in {path}")
    eph = load_file(str(file))
    earth = eph["earth"]
    bodies = {SUN: eph["sun"], MOON: eph["moon"], MERCURY: eph["mercury barycenter"],
              VENUS: eph["venus barycenter"], MARS: eph["mars barycenter"],
              JUPITER: eph["jupiter barycenter"], SATURN: eph["saturn barycenter"]}
    return {"earth": earth, "sun": bodies[SUN],
            "geo": {body: target - earth for body, target in bodies.items()}}


def _eph():
    if _state["ephe_path"] is None:
        raise Error("set_ephe_path() has not been called")
    return _kernel(_state["ephe_path"])


def ephemeris_file(path):
    return Path(path) / EPHEMERIS_FILE


# Spica (α Vir), Hipparcos new reduction (van Leeuwen 2007) via SIMBAD, ICRS J2000.
_SPICA = Star(ra_hours=(13, 25, 11.57937), dec_degrees=(-11, 9, 40.7501),
              ra_mas_per_year=-42.35, dec_mas_per_year=-30.67,
              parallax_mas=13.06, radial_km_per_s=1.0)

# Lahiri (Indian Astronomical Ephemeris): 23°15'00.658" mean ayanamsa on 1956-03-21 0h TT,
# defined with IAU 1976 precession; stored here without that date's nutation.
_LAHIRI_T0, _LAHIRI_AYA0 = 2435553.5, 23.250182778 - 0.004658035


def _polar(v):
    x, y, z = v
    lon = np.degrees(np.arctan2(y, x)) % 360.0
    lat = np.degrees(np.arctan2(z, np.hypot(x, y)))
    return lon, lat, np.sqrt(x * x + y * y + z * z)


def _precession(t):
    # Same matrix as t.P. Skyfield's cached t.P shadows Time.precession_matrix, which
    # t.M still calls, so a Time that has used t.P can no longer give t.M.
    return compute_precession(t.tdb)


def _mean_ecliptic(t):
    """ICRS → mean ecliptic and equinox of date."""
    return mxm(rot_x(-t._mean_obliquity_radians), mxm(_precession(t), ICRS_to_J2000))


def _true_ecliptic(t):
    _, d_eps = t._nutation_angles_radians
    return mxm(rot_x(-(t._mean_obliquity_radians + d_eps)), t.M)


def _spica_mean_longitude(t, truepos):
    astrometric = _eph()["earth"].at(t).observe(_SPICA)
    position = astrometric if truepos else astrometric.apparent()
    return _polar(mxv(_mean_ecliptic(t), position.position.au))[0]


def _iau1976_precession(jd_tt):
    """IAU 1976 (Lieske 1977) precession matrix, J2000 mean equator → mean equator of date."""
    T = (jd_tt - 2451545.0) / 36525.0
    zeta = (2306.2181 * T + 0.30188 * T * T + 0.017998 * T ** 3) * _ASEC
    z = (2306.2181 * T + 1.09468 * T * T + 0.018203 * T ** 3) * _ASEC
    theta = (2004.3109 * T - 0.42665 * T * T - 0.041833 * T ** 3) * _ASEC
    return mxm(rot_z(z), mxm(rot_y(-theta), rot_z(zeta)))


@lru_cache(maxsize=1)
def _lahiri_constants():
    """Vernal point of t0 carried to J2000 by IAU 1976 and back by the current model,
    measured on the mean ecliptic of t0: the offset that keeps Lahiri's definition."""
    t0 = _timescale().tt_jd(_LAHIRI_T0)
    x = mxv(compute_precession(t0.tdb), mxv(_iau1976_precession(_LAHIRI_T0).T, np.array([1.0, 0.0, 0.0])))
    x = mxv(rot_x(-t0._mean_obliquity_radians), x)
    return math.degrees(math.atan2(x[1], x[0])), _mean_ecliptic(t0)


def _lahiri_mean(t):
    correction, ecliptic_t0 = _lahiri_constants()
    vernal_icrs = mxv(np.swapaxes(mxm(_precession(t), ICRS_to_J2000), 0, 1), np.array([1.0, 0.0, 0.0]))
    lon = _polar(mxv(ecliptic_t0, vernal_icrs))[0]
    return (_LAHIRI_AYA0 - lon + correction) % 360.0


def _ayanamsa_mean(t, truepos):
    if _state["sid_mode"] == SIDM_TRUE_CITRA:
        return (_spica_mean_longitude(t, truepos) - 180.0) % 360.0
    if _state["sid_mode"] == SIDM_LAHIRI:
        return _lahiri_mean(t)
    raise Error(f"Unsupported sidereal mode {_state['sid_mode']}")


def _nutation_longitude_degrees(t):
    return np.degrees(t._nutation_angles_radians[0])


def _mean_node(t):
    """Mean lunar node, ELP-2000/82 (Chapront-Touzé & Chapront; Meeus 47.7), mean equinox of date."""
    T = (t.tt - 2451545.0) / 36525.0
    return (125.0445479 - 1934.1362891 * T + 0.0020754 * T * T
            + T ** 3 / 467441.0 - T ** 4 / 60616000.0) % 360.0


def _true_node(geo, frame):
    r, v = mxv(frame, geo.position.au), mxv(frame, geo.velocity.au_per_d)
    h = np.cross(r, v, axis=0)
    return np.degrees(np.arctan2(h[0], -h[1])) % 360.0


class _Instants:
    """One set of UT instants and what every body and frame computed for it shares.

    A chart asks for nine bodies twice (sidereal and tropical) at the same instants;
    the time scale, frame rotations, ayanamsa and each body's position are computed
    once. Values are identical to computing them afresh: the same functions on the
    same Skyfield Time."""

    def __init__(self, jd):
        self.t = _time(jd)
        self._values = {}

    def get(self, key, build):
        if key not in self._values:
            self._values[key] = build()
        return self._values[key]


_INSTANTS = OrderedDict()
_INSTANTS_KEPT = 64


def _instants(jd):
    key = (_state["ephe_path"], jd.tobytes())
    found = _INSTANTS.get(key)
    if found is None:
        found = _INSTANTS[key] = _Instants(jd)
        if len(_INSTANTS) > _INSTANTS_KEPT:
            _INSTANTS.popitem(last=False)
    else:
        _INSTANTS.move_to_end(key)
    return found


def _positions(jd_ut, body, flags):
    """Longitude, latitude and distance arrays for one body at many UT instants."""
    jd = np.ascontiguousarray(np.atleast_1d(np.asarray(jd_ut, dtype=float)))
    shared = _instants(jd)
    t = shared.t
    sidereal = bool(flags & FLG_SIDEREAL)
    mean_frame = sidereal or bool(flags & FLG_NONUT)
    frame = (shared.get("mean_ecliptic", lambda: _mean_ecliptic(t)) if mean_frame
             else shared.get("true_ecliptic", lambda: _true_ecliptic(t)))
    geo = lambda target: shared.get(("geo", target), lambda: _eph()["geo"][target].at(t))
    n = len(jd)
    if body == MEAN_NODE:
        lon = _mean_node(t) + (0.0 if mean_frame else _nutation_longitude_degrees(t))
        lat, dist = np.zeros(n), np.full(n, 0.0025695552898)
    elif body == TRUE_NODE:
        lon, lat, dist = _true_node(geo(MOON), frame), np.zeros(n), np.full(n, 0.00244548)
    elif body in _eph()["geo"]:
        if not flags & FLG_TRUEPOS:
            raise Error("only FLG_TRUEPOS positions are implemented")
        lon, lat, dist = _polar(mxv(frame, geo(body).position.au))
    else:
        raise Error(f"Unsupported body {body}")
    if sidereal:
        truepos = bool(flags & FLG_TRUEPOS)
        lon = (lon - shared.get(("ayanamsa", _state["sid_mode"], truepos),
                                lambda: _ayanamsa_mean(t, truepos))) % 360.0
    return np.atleast_1d(lon), np.atleast_1d(lat), np.atleast_1d(dist)


def _returned_flags(flags):
    ret = (flags & ~EPHEMERIS_MASK) | FLG_SWIEPH if flags & FLG_SWIEPH else flags
    if flags & FLG_TRUEPOS:
        ret |= FLG_NOABERR | FLG_NOGDEFL
    if flags & FLG_SIDEREAL:
        ret |= FLG_NONUT
    return ret


def calc_ut_many(jd_ut, body, flags=FLG_SWIEPH | FLG_SPEED):
    """calc_ut for an array of instants: returns an array of shape (6, n).

    Speeds are central differences of the full computation, as for calc_ut."""
    jd = np.atleast_1d(np.asarray(jd_ut, dtype=float))
    if not flags & FLG_SPEED:
        lon, lat, dist = _positions(jd, body, flags)
        zero = np.zeros_like(jd)
        return np.vstack([lon, lat, dist, zero, zero, zero])
    h = 0.0001 if body in (MOON, TRUE_NODE) else 0.001
    lon, lat, dist = _positions(np.concatenate([jd - h, jd, jd + h]), body, flags)
    n = len(jd)
    (lo_a, lo_m, lo_b), (la_a, la_m, la_b), (di_a, di_m, di_b) = (
        (x[:n], x[n:2 * n], x[2 * n:]) for x in (lon, lat, dist))
    speed = ((lo_b - lo_a + 180.0) % 360.0 - 180.0) / (2 * h)
    return np.vstack([lo_m, la_m, di_m, speed, (la_b - la_a) / (2 * h), (di_b - di_a) / (2 * h)])


def calc_ut(jd_ut, body, flags=FLG_SWIEPH | FLG_SPEED):
    if body == ECL_NUT:
        t = _time(float(jd_ut))
        d_psi, d_eps = (math.degrees(a) for a in t._nutation_angles_radians)
        mean = math.degrees(t._mean_obliquity_radians)
        return (mean + d_eps, mean, d_psi, d_eps, 0.0, 0.0), _returned_flags(flags)
    values = calc_ut_many(float(jd_ut), body, flags)[:, 0]
    return tuple(float(v) for v in values), _returned_flags(flags)


def get_ayanamsa_ut(jd_ut):
    return float(_ayanamsa_mean(_time(float(jd_ut)), truepos=False))


def get_ayanamsa_ex_ut(jd_ut, flags):
    t = _time(float(jd_ut))
    ayanamsa = float(_ayanamsa_mean(t, bool(flags & FLG_TRUEPOS)))
    if not flags & FLG_NONUT:
        ayanamsa += float(_nutation_longitude_degrees(t))
    return _returned_flags(flags), ayanamsa


# ---- configuration -----------------------------------------------------------------------
def set_ephe_path(path=None):
    _state["ephe_path"] = None if path is None else str(path)


def set_sid_mode(mode, t0=0.0, ayan_t0=0.0):
    if mode not in (SIDM_LAHIRI, SIDM_TRUE_CITRA):
        raise Error(f"Unsupported sidereal mode {mode}")
    _state["sid_mode"] = mode


def set_topo(lon, lat, alt=0.0):
    """Accepted for interface parity: every position here is geocentric, as before."""


def julday(year, month, day, hour=12.0, cal=GREG_CAL):
    """Julian Day (Meeus ch. 7); Gregorian calendar only."""
    if cal != GREG_CAL:
        raise Error("only the Gregorian calendar is supported")
    y, m = (year - 1, month + 12) if month <= 2 else (year, month)
    a = math.floor(y / 100)
    b = 2 - a + math.floor(a / 4)
    return math.floor(365.25 * (y + 4716)) + math.floor(30.6001 * (m + 1)) + day + b - 1524.5 + hour / 24.0


# ---- houses, sunrise, equation of time --------------------------------------------------
def houses_ex(jd_ut, lat, lon, hsys=b"W", flags=0):
    """Whole-sign houses; the ascendant and midheaven as Swiss Ephemeris returns them."""
    if hsys not in (b"W", "W"):
        raise Error("only whole-sign houses are implemented")
    t = _time(float(jd_ut))
    d_psi, d_eps = t._nutation_angles_radians
    eps = t._mean_obliquity_radians + d_eps
    armc = (float(t.gast) * 15.0 + lon) % 360.0
    ra, phi = math.radians(armc), math.radians(lat)
    asc = math.degrees(math.atan2(math.cos(ra), -(math.sin(ra) * math.cos(eps)
                                                 + math.tan(phi) * math.sin(eps)))) % 360.0
    mc = math.degrees(math.atan2(math.sin(ra), math.cos(ra) * math.cos(eps))) % 360.0
    if flags & FLG_SIDEREAL:
        shift = float(_ayanamsa_mean(t, bool(flags & FLG_TRUEPOS))) + math.degrees(d_psi)
        asc, mc = (asc - shift) % 360.0, (mc - shift) % 360.0
    first = math.floor(asc / 30.0) * 30.0
    cusps = tuple((first + 30.0 * i) % 360.0 for i in range(12))
    return cusps, (asc, mc, armc, 0.0, 0.0, 0.0, 0.0, 0.0)


def _sun_altitude(jd_ut, lon, lat, alt_m):
    """Altitude of the apparent topocentric centre of the Sun, without refraction.
    Swiss rise_trans keeps only the ephemeris bits of its flags, so FLG_TRUEPOS
    does not apply here: apparent topocentric matches it to 0.002 s."""
    t = _time(jd_ut)
    eph = _eph()
    here = eph["earth"] + wgs84.latlon(lat, lon, elevation_m=alt_m)
    x, y, z = mxv(t.M, here.at(t).observe(eph["sun"]).apparent().position.au)
    ra, dec = np.arctan2(y, x), np.arctan2(z, np.hypot(x, y))
    hour_angle = np.radians(t.gast * 15.0 + lon) - ra
    phi = math.radians(lat)
    return np.degrees(np.arcsin(math.sin(phi) * np.sin(dec) + math.cos(phi) * np.cos(dec) * np.cos(hour_angle)))


_SCAN_STEP = 1.0 / 48.0
_SCAN = np.arange(int(2.0 / _SCAN_STEP) + 2) * _SCAN_STEP
_SUBDIVISIONS = 32


def rise_trans(tjdut, body, rsmi, geopos, atpress=0.0, attemp=0.0, flags=FLG_SWIEPH):
    """Next rise or set of the Sun's centre without refraction after tjdut.

    Returns (0, times) like pyswisseph, or (-2, zeros) when the Sun neither rises
    nor sets within two days. A non-integer rsmi raises TypeError as pyswisseph does."""
    rsmi = operator.index(rsmi)
    if body != SUN or not rsmi & BIT_DISC_CENTER or not rsmi & BIT_NO_REFRACTION:
        raise Error("only the Sun's centre without refraction is implemented")
    lon, lat, alt = (float(v) for v in geopos)
    rising = bool(rsmi & CALC_RISE)
    grid = float(tjdut) + _SCAN
    altitude = _sun_altitude(grid, lon, lat, alt)
    crossing = ((altitude[:-1] < 0) & (altitude[1:] >= 0)) if rising else \
        ((altitude[:-1] >= 0) & (altitude[1:] < 0))
    found = np.flatnonzero(crossing)
    if not len(found):
        return -2, (0.0,) * 10
    a, b = grid[found[0]], grid[found[0] + 1]
    while b - a >= 1e-9:
        points = np.linspace(a, b, _SUBDIVISIONS + 1)
        values = _sun_altitude(points, lon, lat, alt)
        below = values < 0 if rising else values >= 0
        k = int(np.flatnonzero(below[:-1] & ~below[1:])[0])
        a, b = points[k], points[k + 1]
    return 0, (float(b - (b - a) / 2),) + (0.0,) * 9


def time_equ(jd_ut):
    """Equation of time E = LAT − LMT in days, from the apparent Sun and GAST."""
    t = _time(float(jd_ut))
    eph = _eph()
    ra, _, _ = eph["earth"].at(t).observe(eph["sun"]).apparent().radec(epoch=t)
    e = (float(t.gast) * 15.0 - ((float(jd_ut) + 0.5) % 1.0) * 360.0 - ra.hours * 15.0 + 180.0) % 360.0
    return (e - 360.0 if e > 180.0 else e) / 360.0


def pheno_ut(*args, **kwargs):
    raise Error("pheno_ut is not implemented; it was only used by research tools")


def engine_description():
    """What the chart manifests record about the ephemeris engine."""
    return {"engine": "Skyfield + JPL DE440", "ephemeris_file": EPHEMERIS_FILE,
            "delta_t": _delta_t_table()["version"], "skyfield": skyfield.__version__}


version = f"JPL DE440 ({EPHEMERIS_FILE}); ΔT {_delta_t_table()['version']}"
__version__ = f"skyfield {skyfield.__version__}"
