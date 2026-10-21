"""阿什塔库塔（Ashtakoota，36 分合婚）：两颗本命月亮的八项传统对照，以 AstroSage Guna Milan 为准。

八项与满分：Varna 1、Vashya 2、Tara 3、Yoni 4、Graha Maitri 5、Gana 6、Bhakoot 7、Nadi 8。
Varna、Tara、Gana、Bhakoot、Nadi 沿用 vendor/dashaflow/matchmaking.py 的算法；Yoni、Vashya、
Graha Maitri 用下方三张表（vendor 的这三项与 AstroSage 不符，不调用）。20 对虚构资料在 AstroSage
逐项核对一致，见 the TwinSky app's test fixtures 与
the TwinSky app's research note。

只给分数与分项，不给"宜／不宜"之类的传统分档结论。传统上分男方（groom）与女方（bride）；
同性双方按两个方向各算一次。出生时间只精确到日期或时段时，取出生当天整天，月亮在这段时间里
换星宿、换星座或越过射手／摩羯 15° 时分段计算，给出分数范围。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from itertools import product
from typing import Any

from twinsky_engine._vendor.dashaflow.constants import ZODIAC_SIGNS
from twinsky_engine._vendor.dashaflow.matchmaking import GANA, NADI, VARNA, calc_bhakoot, calc_gana, calc_nadi, calc_tara, calc_varna

from . import ids
from .precision import BirthPrecision, birth_precision

METHOD = "ashtakoota_astrosage_v1"
RELATIONSHIPS = frozenset({"lover", "partner", "dating"})
KUTAS = (
    ("varna", "Varna", 1), ("vashya", "Vashya", 2), ("tara", "Tara", 3), ("yoni", "Yoni", 4),
    ("graha_maitri", "Graha Maitri", 5), ("gana", "Gana", 6), ("bhakoot", "Bhakoot", 7), ("nadi", "Nadi", 8),
)
MAX_TOTAL = sum(maximum for _, _, maximum in KUTAS)
NAKSHATRA_SPAN = 360.0 / 27
PADA_SPAN = NAKSHATRA_SPAN / 4

# Yoni（4 分）：14 种动物，表对称（男女方向不影响得分），七对传统死敌为 0。
YONI_ORDER = ("Ashwa", "Gaja", "Mesha", "Sarpa", "Shwana", "Majara", "Mushaka",
              "Gau", "Mahisha", "Vyaghra", "Mriga", "Vanara", "Nakula", "Simha")
YONI_TABLE = (
    (4, 2, 3, 2, 2, 3, 3, 2, 0, 1, 3, 2, 2, 1),
    (2, 4, 3, 2, 2, 3, 2, 3, 3, 1, 3, 2, 2, 0),
    (3, 3, 4, 2, 2, 3, 2, 3, 3, 1, 3, 0, 2, 1),
    (2, 2, 2, 4, 2, 1, 1, 2, 2, 2, 2, 1, 0, 2),
    (2, 2, 2, 2, 4, 1, 1, 2, 2, 2, 0, 2, 2, 2),
    (3, 3, 3, 1, 1, 4, 0, 3, 3, 2, 3, 2, 2, 2),
    (3, 2, 2, 1, 1, 0, 4, 3, 3, 2, 3, 2, 1, 2),
    (2, 3, 3, 2, 2, 3, 3, 4, 3, 0, 3, 2, 2, 1),
    (0, 3, 3, 2, 2, 3, 3, 3, 4, 1, 3, 2, 2, 1),
    (1, 1, 1, 2, 2, 2, 2, 0, 1, 4, 1, 2, 2, 3),
    (3, 3, 3, 2, 0, 3, 3, 3, 3, 1, 4, 2, 2, 1),
    (2, 2, 0, 1, 2, 2, 2, 2, 2, 2, 2, 4, 2, 2),
    (2, 2, 2, 0, 2, 2, 1, 2, 2, 2, 2, 2, 4, 2),
    (1, 0, 1, 2, 2, 2, 2, 1, 1, 3, 1, 2, 2, 4),
)
NAKSHATRA_YONI = ("Ashwa", "Gaja", "Mesha", "Sarpa", "Sarpa", "Shwana", "Majara", "Mesha", "Majara",
                  "Mushaka", "Mushaka", "Gau", "Mahisha", "Vyaghra", "Mahisha", "Vyaghra", "Mriga", "Mriga",
                  "Shwana", "Vanara", "Nakula", "Vanara", "Simha", "Ashwa", "Simha", "Gau", "Gaja")

# Vashya（2 分）：行为女方类别，列为男方类别；不对称。
VASHYA_ORDER = ("Chatushpada", "Nara", "Jalachara", "Vanachara", "Keeta")
VASHYA_TABLE = (
    (2, 1, 1, 0, 1),
    (1, 2, 0.5, 0, 1),
    (1, 0.5, 2, 1, 1),
    (0, 0, 1, 2, 0),
    (1, 0, 1, 0, 2),
)
# 射手座与摩羯座以 15° 为界分前后半宫，其余星座整宫同类。
_VASHYA_BY_SIGN = {
    "aries": "Chatushpada", "taurus": "Chatushpada", "gemini": "Nara", "cancer": "Jalachara",
    "leo": "Vanachara", "virgo": "Nara", "libra": "Nara", "scorpio": "Keeta",
    "sagittarius": ("Nara", "Chatushpada"), "capricorn": ("Chatushpada", "Jalachara"),
    "aquarius": "Nara", "pisces": "Jalachara",
}

# Graha Maitri（5 分）：月亮星座主星的自然友敌（帕拉夏拉通行表），主星相同视为友。
SIGN_LORDS = ("mars", "venus", "mercury", "moon", "sun", "mercury", "venus", "mars", "jupiter", "saturn", "saturn",
              "jupiter")
_NATURAL = {  # 主星: (友, 中立)；其余为敌。
    "sun": ({"moon", "mars", "jupiter"}, {"mercury"}),
    "moon": ({"sun", "mercury"}, {"mars", "jupiter", "venus", "saturn"}),
    "mars": ({"sun", "moon", "jupiter"}, {"venus", "saturn"}),
    "mercury": ({"sun", "venus"}, {"mars", "jupiter", "saturn"}),
    "jupiter": ({"sun", "moon", "mars"}, {"saturn"}),
    "venus": ({"mercury", "saturn"}, {"mars", "jupiter"}),
    "saturn": ({"mercury", "venus"}, {"jupiter"}),
}
_MAITRI = {("friend", "friend"): 5, ("friend", "neutral"): 4, ("neutral", "neutral"): 3,
           ("enemy", "friend"): 1, ("enemy", "neutral"): 0.5, ("enemy", "enemy"): 0}

VARNA_NAMES = {1: "Brahmin", 2: "Kshatriya", 3: "Vaishya", 4: "Shudra"}
NAKSHATRA_DISPLAY = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha",
    "Magha", "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha",
    "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
)
RASI_ZH = {"aries": "白羊座", "taurus": "金牛座", "gemini": "双子座", "cancer": "巨蟹座", "leo": "狮子座",
           "virgo": "处女座", "libra": "天秤座", "scorpio": "天蝎座", "sagittarius": "射手座",
           "capricorn": "摩羯座", "aquarius": "水瓶座", "pisces": "双鱼座"}
LORD_ZH = {"sun": "太阳", "moon": "月亮", "mars": "火星", "mercury": "水星", "jupiter": "木星", "venus": "金星",
           "saturn": "土星"}
VARNA_ZH = {"Brahmin": "婆罗门", "Kshatriya": "刹帝利", "Vaishya": "吠舍", "Shudra": "首陀罗"}
VASHYA_ZH = {"Chatushpada": "四足", "Nara": "人类", "Jalachara": "水生", "Vanachara": "野兽", "Keeta": "虫类"}
YONI_ZH = {"Ashwa": "马", "Gaja": "象", "Mesha": "羊", "Sarpa": "蛇", "Shwana": "狗", "Majara": "猫", "Mushaka": "鼠",
           "Gau": "牛", "Mahisha": "水牛", "Vyaghra": "虎", "Mriga": "鹿", "Vanara": "猴", "Nakula": "獴", "Simha": "狮"}
GANA_ZH = {"Deva": "天神", "Manushya": "人", "Rakshasa": "罗刹"}
NADI_ZH = {"Adi": "初脉 Adi", "Madhya": "中脉 Madhya", "Antya": "末脉 Antya"}


def moon_place(longitude: float) -> dict[str, Any]:
    """一颗月亮（恒星黄道经度）在八项里用到的全部归类。"""
    longitude %= 360
    rasi_index = int(longitude // 30)
    rasi = ids.RASIS[rasi_index]
    nak = int(longitude // NAKSHATRA_SPAN) % 27
    vashya = _VASHYA_BY_SIGN[rasi]
    if isinstance(vashya, tuple):
        vashya = vashya[longitude % 30 >= 15]
    return {
        "longitude": round(longitude, 4),
        "rasi": rasi, "nakshatra": ids.NAKSHATRAS[nak], "nakshatra_name": NAKSHATRA_DISPLAY[nak],
        "pada": int(longitude % NAKSHATRA_SPAN // PADA_SPAN) + 1,
        "varna": VARNA_NAMES[VARNA[ZODIAC_SIGNS[rasi_index]]], "vashya": vashya, "yoni": NAKSHATRA_YONI[nak],
        "lord": SIGN_LORDS[rasi_index], "gana": GANA[nak], "nadi": NADI[nak],
    }


def _relation(lord: str, other: str) -> str:
    if lord == other:
        return "friend"
    friends, neutral = _NATURAL[lord]
    return "friend" if other in friends else "neutral" if other in neutral else "enemy"


def graha_maitri(groom_lord: str, bride_lord: str) -> float:
    pair = tuple(sorted((_relation(groom_lord, bride_lord), _relation(bride_lord, groom_lord))))
    return _MAITRI[pair]


def score(groom_longitude: float, bride_longitude: float) -> dict[str, float]:
    """八项得分；groom 为传统上的男方，bride 为女方。"""
    groom, bride = moon_place(groom_longitude), moon_place(bride_longitude)
    g_sign, b_sign = ZODIAC_SIGNS[ids.RASIS.index(groom["rasi"])], ZODIAC_SIGNS[ids.RASIS.index(bride["rasi"])]
    g_nak, b_nak = ids.NAKSHATRAS.index(groom["nakshatra"]), ids.NAKSHATRAS.index(bride["nakshatra"])
    return {
        "varna": calc_varna(g_sign, b_sign),
        "vashya": float(VASHYA_TABLE[VASHYA_ORDER.index(bride["vashya"])][VASHYA_ORDER.index(groom["vashya"])]),
        "tara": calc_tara(g_nak, b_nak),
        "yoni": float(YONI_TABLE[YONI_ORDER.index(bride["yoni"])][YONI_ORDER.index(groom["yoni"])]),
        "graha_maitri": float(graha_maitri(groom["lord"], bride["lord"])),
        "gana": calc_gana(g_nak, b_nak),
        "bhakoot": calc_bhakoot(g_sign, b_sign),
        "nadi": calc_nadi(g_nak, b_nak),
    }


def _bhakoot_distance(groom: dict[str, Any], bride: dict[str, Any]) -> str:
    forward = (ids.RASIS.index(bride["rasi"]) - ids.RASIS.index(groom["rasi"])) % 12 + 1
    backward = (14 - forward) % 12 or 12
    return f"{min(forward, backward)}/{max(forward, backward)}"


def _details(groom: dict[str, Any], bride: dict[str, Any]) -> dict[str, str]:
    """每项双方各自的归类，男方在前；只描述归类，不作评价。"""
    return {
        "varna": f"{VARNA_ZH[groom['varna']]} · {VARNA_ZH[bride['varna']]}",
        "vashya": f"{VASHYA_ZH[groom['vashya']]} · {VASHYA_ZH[bride['vashya']]}",
        "tara": f"{groom['nakshatra_name']} · {bride['nakshatra_name']}",
        "yoni": f"{YONI_ZH[groom['yoni']]} · {YONI_ZH[bride['yoni']]}",
        "graha_maitri": f"{LORD_ZH[groom['lord']]} · {LORD_ZH[bride['lord']]}",
        "gana": f"{GANA_ZH[groom['gana']]} · {GANA_ZH[bride['gana']]}",
        "bhakoot": f"{RASI_ZH[groom['rasi']]} · {RASI_ZH[bride['rasi']]}，相距 {_bhakoot_distance(groom, bride)}",
        "nadi": f"{NADI_ZH[groom['nadi']]} · {NADI_ZH[bride['nadi']]}",
    }


