"""盘面元素 ID 的唯一生成入口。"""

from __future__ import annotations

import re
from typing import Iterable, Literal

PILLARS = ("year", "month", "day", "hour")
HIDDEN_LAYERS = ("benqi", "zhongqi", "yuqi")
GRAHAS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu", "ketu")
RASIS = ("aries", "taurus", "gemini", "cancer", "leo", "virgo", "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces")
NAKSHATRAS = ("ashwini", "bharani", "krittika", "rohini", "mrigashira", "ardra", "punarvasu", "pushya", "ashlesha", "magha", "purvaphalguni", "uttaraphalguni", "hasta", "chitra", "swati", "vishakha", "anuradha", "jyeshtha", "mula", "purvashadha", "uttarashadha", "shravana", "dhanishta", "shatabhisha", "purvabhadrapada", "uttarabhadrapada", "revati")
SHODASHAVARGAS = (
    "d1", "d2", "d3", "d4", "d7", "d9", "d10", "d12",
    "d16", "d20", "d24", "d27", "d30", "d40", "d45", "d60",
)
EXTENDED_VARGAS = ("d5", "d6", "d8", "d11")
VARGAS = (
    "d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8", "d9", "d10",
    "d11", "d12", "d16", "d20", "d24", "d27", "d30", "d40", "d45", "d60",
)
Pillar = Literal["year", "month", "day", "hour"]


def bz_pillar(pillar: Pillar) -> str:
    _check(pillar, PILLARS, "pillar")
    return f"bz.pillar.{pillar}"


def bz_stem(pillar: Pillar) -> str:
    _check(pillar, PILLARS, "pillar")
    return f"bz.stem.{pillar}"


def bz_branch(pillar: Pillar) -> str:
    _check(pillar, PILLARS, "pillar")
    return f"bz.branch.{pillar}"


def bz_hidden(pillar: Pillar, layer: str) -> str:
    _check(pillar, PILLARS, "pillar")
    _check(layer, HIDDEN_LAYERS, "hidden layer")
    return f"bz.hidden.{pillar}.{layer}"


def bz_siling() -> str:
    return "bz.siling.month"


def bz_geju() -> str:
    return "bz.geju"


def bz_dayun(n: int) -> str:
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"大运序号须为正整数，收到 {n!r}")
    return f"bz.dayun.{n}"


def bz_liunian(year: int) -> str:
    if not isinstance(year, int):
        raise ValueError(f"流年须为整数年份，收到 {year!r}")
    return f"bz.liunian.{year}"


def bz_liuyue(year: int, month_index: int) -> str:
    if not isinstance(year, int):
        raise ValueError(f"流月年份须为整数，收到 {year!r}")
    if not isinstance(month_index, int) or not 1 <= month_index <= 12:
        raise ValueError(f"流月序号须为 1-12，收到 {month_index!r}")
    return f"bz.liuyue.{year}.{month_index}"


def bz_liuri(value: str) -> str:
    if not re.fullmatch(r"(?:19|20|21)\d{2}-\d{2}-\d{2}", value):
        raise ValueError(f"流日日期须为 YYYY-MM-DD，收到 {value!r}")
    return f"bz.liuri.{value}"


def vd_lagna(varga: str = "d1") -> str:
    _check(varga, VARGAS, "varga")
    return "vd.lagna" if varga == "d1" else f"vd.{varga}.lagna"


def vd_house(n: int, varga: str = "d1") -> str:
    if not isinstance(n, int) or not 1 <= n <= 12:
        raise ValueError(f"宫位须为 1-12，收到 {n!r}")
    _check(varga, VARGAS, "varga")
    return f"vd.house.{n}" if varga == "d1" else f"vd.{varga}.house.{n}"


def vd_graha(graha: str, varga: str = "d1") -> str:
    _check(graha, GRAHAS, "graha")
    _check(varga, VARGAS, "varga")
    return f"vd.graha.{graha}" if varga == "d1" else f"vd.{varga}.graha.{graha}"


def vd_rasi(rasi: str, varga: str = "d1") -> str:
    _check(rasi, RASIS, "rasi")
    _check(varga, VARGAS, "varga")
    return f"vd.rasi.{rasi}" if varga == "d1" else f"vd.{varga}.rasi.{rasi}"


def vd_nak(nak: str) -> str:
    _check(nak, NAKSHATRAS, "nakshatra")
    return f"vd.nak.{nak}"


def vd_dasha(*grahas: str) -> str:
    if not grahas:
        raise ValueError("至少需要一个行星")
    for graha in grahas:
        _check(graha, GRAHAS, "graha")
    return "vd.dasha." + ".".join(grahas)


def vd_transit(value: str, graha: str) -> str:
    if not re.fullmatch(r"(?:19|20|21)\d{2}-\d{2}-\d{2}", value):
        raise ValueError(f"行运日期须为 YYYY-MM-DD，收到 {value!r}")
    _check(graha, GRAHAS, "graha")
    return f"vd.transit.{value}.{graha}"


def vd_yoga(name: str, n: int = 1) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise ValueError(f"yoga 名须为小写标识符，收到 {name!r}")
    if not isinstance(n, int) or n < 1:
        raise ValueError(f"序号须为正整数，收到 {n!r}")
    return f"vd.yoga.{name}.{n}"


_VARGA_PATTERN = "|".join(item for item in VARGAS if item != "d1")


_PATTERNS = (
    re.compile(r"^bz\.pillar\.(year|month|day|hour)$"),
    re.compile(r"^bz\.(stem|branch)\.(year|month|day|hour)$"),
    re.compile(r"^bz\.hidden\.(year|month|day|hour)\.(benqi|zhongqi|yuqi)$"),
    re.compile(r"^bz\.siling\.month$"),
    re.compile(r"^bz\.geju$"),
    re.compile(r"^bz\.dayun\.\d+$"),
    re.compile(r"^bz\.liunian\.\d{1,4}$"),
    re.compile(r"^bz\.liuyue\.(?:19|20|21)\d{2}\.(?:1[0-2]|[1-9])$"),
    re.compile(r"^bz\.liuri\.(?:19|20|21)\d{2}-\d{2}-\d{2}$"),
    re.compile(r"^vd\.lagna$"),
    re.compile(r"^vd\.house\.(1[0-2]|[1-9])$"),
    re.compile(r"^vd\.(" + _VARGA_PATTERN + r")\.lagna$"),
    re.compile(r"^vd\.(" + _VARGA_PATTERN + r")\.house\.(1[0-2]|[1-9])$"),
    re.compile(r"^vd\.(" + _VARGA_PATTERN + r")\.graha\.(" + "|".join(GRAHAS) + r")$"),
    re.compile(r"^vd\.(" + _VARGA_PATTERN + r")\.rasi\.(" + "|".join(RASIS) + r")$"),
    re.compile(r"^vd\.graha\.(" + "|".join(GRAHAS) + r")$"),
    re.compile(r"^vd\.rasi\.(" + "|".join(RASIS) + r")$"),
    re.compile(r"^vd\.nak\.(" + "|".join(NAKSHATRAS) + r")$"),
    re.compile(r"^vd\.dasha\.(" + "|".join(GRAHAS) + r")(\.(" + "|".join(GRAHAS) + r"))*$"),
    re.compile(r"^vd\.transit\.(?:19|20|21)\d{2}-\d{2}-\d{2}\.(" + "|".join(GRAHAS) + r")$"),
    re.compile(r"^vd\.yoga\.[a-z][a-z0-9_]*\.\d+$"),
)


def is_valid(element_id: str) -> bool:
    return any(pattern.match(element_id) for pattern in _PATTERNS)


def validate_all(ids: Iterable[str]) -> None:
    bad = [element_id for element_id in ids if not is_valid(element_id)]
    if bad:
        raise ValueError(f"非法 ID：{bad}")


def system_of(element_id: str) -> str:
    if element_id.startswith("bz."):
        return "bazi"
    if element_id.startswith("vd."):
        return "vedic"
    raise ValueError(f"无法识别的 ID：{element_id!r}")


def _check(value: str, allowed: tuple, label: str) -> None:
    if value not in allowed:
        raise ValueError(f"非法 {label}：{value!r}，可选 {allowed}")
