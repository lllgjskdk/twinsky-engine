"""八字规则中的静态配置。"""

from __future__ import annotations

from math import isfinite
from typing import TypeAlias

# 每项为（藏干层级、天干、司令天数），按余气 → 中气 → 本气排列。
# 依据《渊海子平》传统人元司事分野；藏干与司令均从本表投影，禁止分源。
SilingPeriods: TypeAlias = tuple[tuple[str, int], ...]
HIDDEN_STEM_RULES: dict[str, tuple[tuple[str, str, int], ...]] = {
    "子": (("yuqi", "壬", 10), ("benqi", "癸", 20)),
    "丑": (("yuqi", "癸", 9), ("zhongqi", "辛", 3), ("benqi", "己", 18)),
    "寅": (("yuqi", "戊", 7), ("zhongqi", "丙", 7), ("benqi", "甲", 16)),
    "卯": (("yuqi", "甲", 10), ("benqi", "乙", 20)),
    "辰": (("yuqi", "乙", 9), ("zhongqi", "癸", 3), ("benqi", "戊", 18)),
    "巳": (("yuqi", "戊", 7), ("zhongqi", "庚", 7), ("benqi", "丙", 16)),
    "午": (("yuqi", "丙", 10), ("zhongqi", "己", 9), ("benqi", "丁", 11)),
    "未": (("yuqi", "丁", 9), ("zhongqi", "乙", 3), ("benqi", "己", 18)),
    "申": (("yuqi", "戊", 7), ("zhongqi", "壬", 7), ("benqi", "庚", 16)),
    "酉": (("yuqi", "庚", 10), ("benqi", "辛", 20)),
    "戌": (("yuqi", "辛", 9), ("zhongqi", "丁", 3), ("benqi", "戊", 18)),
    "亥": (("yuqi", "戊", 7), ("zhongqi", "甲", 7), ("benqi", "壬", 16)),
}
SILING_DAY_TABLE: dict[str, SilingPeriods] = {
    branch: tuple((stem, days) for _, stem, days in rules)
    for branch, rules in HIDDEN_STEM_RULES.items()
}

HALF_COMBINATION_COUNTS = False
POSITION_WEIGHT = {"stem": 1.0, "month_hidden": 0.65, "hidden": 0.35}
ANSWER_GE_PENALTY = 0.6
# 分盘仅验证 D1 承诺。Vargottama 是同一角色的加权确认，不是新增证据。
VARGOTTAMA_MULTIPLIER = 1.5
# 小运从时柱本身或下一柱起算。各家有异，保留为显式配置。
XIAO_YUN_START = "next"

# 地支关系表作为通用规则源，业务模块不重复手写组合。
BRANCH_SIX_COMBINATIONS = (
    frozenset({"子", "丑"}), frozenset({"寅", "亥"}),
    frozenset({"卯", "戌"}), frozenset({"辰", "酉"}),
    frozenset({"巳", "申"}), frozenset({"午", "未"}),
)
BRANCH_SIX_CLASHES = (
    frozenset({"子", "午"}), frozenset({"丑", "未"}),
    frozenset({"寅", "申"}), frozenset({"卯", "酉"}),
    frozenset({"辰", "戌"}), frozenset({"巳", "亥"}),
)
BRANCH_SIX_HARMS = (
    frozenset({"子", "未"}), frozenset({"丑", "午"}),
    frozenset({"寅", "巳"}), frozenset({"卯", "辰"}),
    frozenset({"申", "亥"}), frozenset({"酉", "戌"}),
)


def branch_relation(first: str, second: str) -> str | None:
    """返回两个不同地支之间的六合、六冲或六害关系。"""
    pair = frozenset({first, second})
    if len(pair) != 2:
        return None
    for name, table in (
        ("六合", BRANCH_SIX_COMBINATIONS),
        ("六冲", BRANCH_SIX_CLASHES),
        ("六害", BRANCH_SIX_HARMS),
    ):
        if pair in table:
            return name
    return None


def hidden_stems_of(branch: str) -> dict[str, str | None]:
    """从唯一规则源取得地支藏干，按本气／中气／余气组织。"""
    if branch not in HIDDEN_STEM_RULES:
        raise ValueError(f"未知地支：{branch!r}")
    result: dict[str, str | None] = {"benqi": None, "zhongqi": None, "yuqi": None}
    for layer, stem, _ in HIDDEN_STEM_RULES[branch]:
        result[layer] = stem
    return result


def validate_siling_day_table() -> None:
    """校验人元司事分日表，防止任一月份的口径不完整。"""
    for branch, periods in SILING_DAY_TABLE.items():
        total = sum(days for _, days in periods)
        if total != 30:
            raise ValueError(f"{branch} 月司令分日合计须为 30，收到 {total}")


def siling_at(branch: str, days_into_month: float) -> tuple[str, int]:
    """取得入月时刻对应的司令天干与该司令段的总天数。"""
    if branch not in SILING_DAY_TABLE:
        raise ValueError(f"未知月支：{branch!r}")
    if not isfinite(days_into_month) or days_into_month < 0.0:
        raise ValueError(f"入月天数须为非负有限数，收到 {days_into_month!r}")

    elapsed = 0.0
    for stem, days in SILING_DAY_TABLE[branch]:
        if days_into_month < elapsed + days:
            return stem, days
        elapsed += days
    # 节令实际长度偶有超过传统分日表的 30 日；交下一个节前仍归本气段。
    return SILING_DAY_TABLE[branch][-1]


validate_siling_day_table()
