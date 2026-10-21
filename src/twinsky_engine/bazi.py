"""八字四柱排盘。"""

from __future__ import annotations

from calendar import monthrange
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timedelta

from lunar_python import Lunar, Solar

from . import ids
from . import constants
from .solar_time import longitude_correction_minutes
from .schema import (
    BaziChart,
    BirthInput,
    DaYunPeriod,
    Evidence,
    GeJuCandidate,
    GeJuGod,
    GeJuResolutionStatus,
    GeJuYongShen,
    LiuNian,
    Polarity,
    QiYun,
    System,
    SolarTimeMode,
    XiaoYun,
    XiangShen,
    XiangShenResolutionStatus,
    ZiShiRule,
)

PILLAR_NAMES = ("year", "month", "day", "hour")
HIDDEN_STEM_LAYERS = ("benqi", "zhongqi", "yuqi")

STEM_PROPERTIES = {
    "甲": ("wood", "yang"), "乙": ("wood", "yin"),
    "丙": ("fire", "yang"), "丁": ("fire", "yin"),
    "戊": ("earth", "yang"), "己": ("earth", "yin"),
    "庚": ("metal", "yang"), "辛": ("metal", "yin"),
    "壬": ("water", "yang"), "癸": ("water", "yin"),
}
PRODUCES = {"wood": "fire", "fire": "earth", "earth": "metal", "metal": "water", "water": "wood"}
CONTROLS = {"wood": "earth", "earth": "water", "water": "fire", "fire": "metal", "metal": "wood"}

GRID_BY_TEN_GOD = {
    "正官": "正官格",
    "七杀": "七杀格",
    "正财": "正财格",
    "偏财": "偏财格",
    "正印": "正印格",
    "偏印": "偏印格",
    "食神": "食神格",
    "伤官": "伤官格",
}
GRID_TEN_GOD = {
    **{grid: ten_god_name for ten_god_name, grid in GRID_BY_TEN_GOD.items()},
    "建禄格": "比肩",
    "月劫格": "劫财",
    "阳刃格": "劫财",
}
REGULAR_GRIDS = frozenset({"正官格", "正财格", "偏财格", "食神格"})
REVERSE_GRIDS = frozenset({"七杀格"})
SPECIAL_GRIDS = frozenset({"正印格", "偏印格", "伤官格", "建禄格", "月劫格", "阳刃格"})
# A new grid must explicitly register a handler; a passing cast is not coverage.
EVALUATED_GRIDS = REGULAR_GRIDS | REVERSE_GRIDS | SPECIAL_GRIDS
PATTERN_RULE_VERSION = "bazi-structural-paths-20260907-v2"

THREE_COMBINATIONS = (
    (frozenset({"申", "子", "辰"}), "water"),
    (frozenset({"亥", "卯", "未"}), "wood"),
    (frozenset({"寅", "午", "戌"}), "fire"),
    (frozenset({"巳", "酉", "丑"}), "metal"),
)
THREE_MEETINGS = (
    (frozenset({"寅", "卯", "辰"}), "wood"),
    (frozenset({"巳", "午", "未"}), "fire"),
    (frozenset({"申", "酉", "戌"}), "metal"),
    (frozenset({"亥", "子", "丑"}), "water"),
)
STEM_COMBINATIONS = {
    frozenset({"甲", "己"}), frozenset({"乙", "庚"}),
    frozenset({"丙", "辛"}), frozenset({"丁", "壬"}),
    frozenset({"戊", "癸"}),
}
LU_TABLE = {
    "甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
    "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子",
}
REN_TABLE = {
    "甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子",
}
STEMS = tuple(STEM_PROPERTIES)
BRANCHES = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")
JIE_DISPLAY_NAMES = {
    "DA_XUE": "大雪",
    "XIAO_HAN": "小寒",
    "LI_CHUN": "立春",
    "JING_ZHE": "惊蛰",
}
LUNAR_PYTHON_REFERENCE_TZ_OFFSET = 8.0


def cast(
    birth: BirthInput,
    zishi_rule: ZiShiRule,
    include_analysis: bool = True,
    dayun_steps: int = 8,
    liunian_year_range: tuple[int, int] | None = None,
) -> BaziChart:
    """使用出生信息中的有效时间排出四柱。

    ``zishi_rule`` 必须由调用方明确传入，避免在 the TwinSky project spec §10 尚未定案时
    隐式选定早晚子时规则。月柱由 lunar-python 的精确节气接口计算。
    """
    effective_time = _local_naive(birth.effective_time)
    term_shift_minutes = _term_shift_minutes(birth)
    # lunar-python's ephemeris timestamps are standard-time clock readings.
    # Move them into the same local-solar clock as the active birth time before
    # deciding month/year boundaries; day/hour still use the effective time.
    term_time = effective_time - timedelta(minutes=term_shift_minutes)
    lunar = _to_lunar(effective_time)
    term_lunar = _to_lunar(term_time)
    pillars = _pillars(lunar, term_lunar, effective_time, zishi_rule)
    stems = {name: pillar[0] for name, pillar in pillars.items()}
    branches = {name: pillar[1] for name, pillar in pillars.items()}
    hidden_stems = {
        name: _hidden_stems(branch)
        for name, branch in branches.items()
    }
    siling, siling_depth = _siling(term_lunar, term_time, branches["month"])

    chart = BaziChart(
        birth=birth,
        zishi_rule=zishi_rule,
        pillars=pillars,
        stems=stems,
        branches=branches,
        hidden_stems=hidden_stems,
        day_master=stems["day"],
        siling=siling,
        siling_depth=siling_depth,
    )
    if include_analysis:
        analyze(chart)
    populate_fortune_cycles(chart, dayun_steps, liunian_year_range)
    return chart


def four_pillars(birth: BirthInput, zishi_rule: ZiShiRule) -> dict[str, str]:
    """只取四柱，口径与 ``cast`` 相同；供出生时段内逐时刻比较。"""
    effective_time = _local_naive(birth.effective_time)
    term_time = effective_time - timedelta(minutes=_term_shift_minutes(birth))
    return _pillars(_to_lunar(effective_time), _to_lunar(term_time), effective_time, zishi_rule)


def _to_lunar(moment: datetime) -> Lunar:
    """以 lunar-python 创建含精确节气信息的农历对象。"""
    return Solar.fromYmdHms(
        moment.year,
        moment.month,
        moment.day,
        moment.hour,
        moment.minute,
        moment.second,
    ).getLunar()


def _pillars(
    lunar: Lunar,
    term_lunar: Lunar,
    moment: datetime,
    zishi_rule: ZiShiRule,
) -> dict[str, str]:
    """取得年、月、日、时四柱；年、月均使用库的精确节气结果。"""
    return {
        "year": term_lunar.getYearInGanZhiExact(),
        "month": term_lunar.getMonthInGanZhiExact(),
        "day": _day_pillar(lunar, moment, zishi_rule),
        "hour": lunar.getTimeInGanZhi(),
    }


def _day_pillar(lunar: Lunar, moment: datetime, zishi_rule: ZiShiRule) -> str:
    """依配置处理晚子时的日柱归属。"""
    if zishi_rule is ZiShiRule.NO_SWITCH:
        return lunar.getDayInGanZhiExact2()
    if zishi_rule is ZiShiRule.SWITCH:
        return lunar.getDayInGanZhiExact()
    if zishi_rule is ZiShiRule.SPLIT:
        # 早晚子时分算：晚子时保留当日，早子时按自然日所属日柱计算。
        return (
            lunar.getDayInGanZhiExact2()
            if moment.hour == 23
            else lunar.getDayInGanZhiExact()
        )
    raise ValueError(f"不支持的子时规则：{zishi_rule!r}")


def _hidden_stems(branch: str) -> dict[str, str | None]:
    """从 constants 的唯一藏干／司令规则源取得三层藏干。"""
    return constants.hidden_stems_of(branch)


def _siling(lunar: Lunar, moment: datetime, month_branch: str) -> tuple[str, int]:
    """根据精确交节时刻与人元司事表取得月令司令。"""
    return constants.siling_at(month_branch, _days_into_solar_term(lunar, moment))


def _days_into_solar_term(lunar: Lunar, moment: datetime) -> float:
    """返回距当前节令交接时刻的天数，保留分钟级以下精度。"""
    try:
        prior_moment = moment.replace(year=moment.year - 1)
    except ValueError:
        prior_moment = moment.replace(year=moment.year - 1, day=28)
    prior_lunar = _to_lunar(prior_moment)
    jie_qi_table = {**prior_lunar.getJieQiTable(), **lunar.getJieQiTable()}
    starts = [
        _solar_to_datetime(jie_qi_table[name])
        for name in Lunar.JIE_QI_IN_USE[::2]
        if name in jie_qi_table
    ]
    candidates = [start for start in starts if start <= moment]
    if not candidates:
        return 0.0
    active_start = max(candidates)
    return (moment - active_start).total_seconds() / 86_400


def _solar_to_datetime(solar: Solar) -> datetime:
    """转换 lunar-python 的 Solar 对象，避免自行进行历法换算。"""
    return datetime(
        solar.getYear(),
        solar.getMonth(),
        solar.getDay(),
        solar.getHour(),
        solar.getMinute(),
        solar.getSecond(),
    )


def _local_naive(moment: datetime) -> datetime:
    """lunar-python 接收出生地民用时间；时区信息由 BirthInput 单独保存。"""
    return moment.replace(tzinfo=None)


def _term_shift_minutes(birth: BirthInput) -> float:
    """返回节气从 lunar-python 东八区时钟移到当前有效时钟的偏移。"""
    longitude_shift = longitude_correction_minutes(
        birth.lng,
        LUNAR_PYTHON_REFERENCE_TZ_OFFSET,
    )
    if birth.active_mode is SolarTimeMode.LONGITUDE:
        return longitude_shift
    if birth.active_mode is SolarTimeMode.LONGITUDE_EOT:
        effective = _local_naive(birth.effective_time)
        raw = _local_naive(birth.raw_datetime)
        local_shift = longitude_correction_minutes(birth.lng, birth.tz_offset)
        equation_of_time_shift = (effective - raw).total_seconds() / 60.0 - local_shift
        return longitude_shift + equation_of_time_shift
    return 0.0


def calculate_qi_yun(chart: BaziChart) -> QiYun:
    """按年干阴阳、性别及十二节的精确时刻计算起运。"""
    birth_time = _local_naive(chart.birth.effective_time)
    forward = _is_forward_direction(chart.stems["year"], chart.birth.gender)
    target_name, target_time = _target_jie(
        birth_time,
        forward,
        term_shift_minutes=_term_shift_minutes(chart.birth),
    )
    elapsed_seconds = abs((target_time - birth_time).total_seconds())
    age_years, age_months, age_days = _qi_yun_age(elapsed_seconds)
    result = QiYun(
        direction="forward" if forward else "backward",
        target_jie=target_name,
        target_jie_at=target_time,
        elapsed_seconds=elapsed_seconds,
        age_years=age_years,
        age_months=age_months,
        age_days=age_days,
        start_date=_add_calendar_duration(birth_time, age_years, age_months, age_days),
    )
    chart.qi_yun = result
    return result


def calculate_da_yun(chart: BaziChart, steps: int = 8) -> list[DaYunPeriod]:
    """自月柱顺逆推进，生成八至十步、每步十年的大运。"""
    if not 8 <= steps <= 10:
        raise ValueError(f"大运步数须为 8-10，收到 {steps}")
    qi_yun = chart.qi_yun or calculate_qi_yun(chart)
    step = 1 if qi_yun.direction == "forward" else -1
    periods: list[DaYunPeriod] = []
    for index in range(1, steps + 1):
        pillar = _advance_pillar(chart.pillars["month"], step * index)
        start_date = _add_calendar_duration(qi_yun.start_date, (index - 1) * 10, 0, 0.0)
        end_date = _add_calendar_duration(start_date, 10, 0, 0.0)
        periods.append(DaYunPeriod(
            id=ids.bz_dayun(index),
            index=index,
            pillar=pillar,
            stem=pillar[0],
            branch=pillar[1],
            stem_ten_god=ten_god(chart.day_master, pillar[0]),
            branch_ten_gods=_branch_ten_gods(chart.day_master, pillar[1]),
            start_year=start_date.year,
            end_year=end_date.year,
            start_date=start_date,
            end_date=end_date,
        ))
    chart.da_yun = periods
    return periods


def calculate_liu_nian(chart: BaziChart, start_year: int, end_year: int) -> list[LiuNian]:
    """按立春换年，计算闭区间内每一年的流年干支与十神。"""
    if start_year > end_year:
        raise ValueError(f"流年起始年份不得晚于结束年份：{start_year} > {end_year}")
    years: list[LiuNian] = []
    for year in range(start_year, end_year + 1):
        pillar = _year_pillar_at_lichun(year)
        years.append(LiuNian(
            id=ids.bz_liunian(year),
            year=year,
            pillar=pillar,
            stem=pillar[0],
            branch=pillar[1],
            stem_ten_god=ten_god(chart.day_master, pillar[0]),
            branch_ten_gods=_branch_ten_gods(chart.day_master, pillar[1]),
        ))
    chart.liu_nian = years
    return years


def liu_yue_calendar(chart: BaziChart, year: int) -> list[dict[str, object]]:
    """按立春至次年立春的十二个节月排出流月。"""
    term_shift_minutes = _term_shift_minutes(chart.birth)
    start = _lichun_at(year, term_shift_minutes)
    end = _lichun_at(year + 1, term_shift_minutes)
    boundaries = sorted({
        at + timedelta(minutes=term_shift_minutes): name
        for name, at in _jie_datetimes_around(datetime(year, 7, 1, 12))
        if start <= at + timedelta(minutes=term_shift_minutes) <= end
    }.items())
    if len(boundaries) != 13:
        raise ValueError(f"{year} 年节月边界应为 13 个，实际为 {len(boundaries)} 个")

    year_stem = _year_pillar_at_lichun(year)[0]
    first_month_stem = (STEMS.index(year_stem) % 5 * 2 + 2) % len(STEMS)
    months = []
    for index, ((starts_at, jie), (ends_at, _)) in enumerate(zip(boundaries, boundaries[1:]), 1):
        stem = STEMS[(first_month_stem + index - 1) % len(STEMS)]
        branch = BRANCHES[(index + 1) % len(BRANCHES)]
        months.append({
            "index": index,
            "pillar": stem + branch,
            "stem": stem,
            "branch": branch,
            "stem_ten_god": ten_god(chart.day_master, stem),
            "jie": jie,
            "starts_at": starts_at,
            "ends_at": ends_at,
        })
    return months


def liu_ri_calendar(chart: BaziChart, year: int, month_index: int) -> list[dict[str, object]]:
    """排出指定节月内的流日；边界日以当地正午所属节月归类。"""
    months = liu_yue_calendar(chart, year)
    if not 1 <= month_index <= len(months):
        raise ValueError(f"流月序号须为 1-12，收到 {month_index!r}")
    month = months[month_index - 1]
    starts_at = month["starts_at"]
    ends_at = month["ends_at"]
    cursor = starts_at.date()
    final_date = ends_at.date()
    days = []
    while cursor <= final_date:
        noon = datetime(cursor.year, cursor.month, cursor.day, 12)
        if starts_at <= noon < ends_at:
            lunar = _to_lunar(noon)
            pillar = _day_pillar(lunar, noon, chart.zishi_rule)
            days.append({
                "date": cursor,
                "pillar": pillar,
                "stem": pillar[0],
                "branch": pillar[1],
                "stem_ten_god": ten_god(chart.day_master, pillar[0]),
            })
        cursor += timedelta(days=1)
    return days


def calculate_xiao_yun(chart: BaziChart) -> list[XiaoYun]:
    """排出出生至交运前、以立春为年界的一年一位小运。"""
    if constants.XIAO_YUN_START not in {"self", "next"}:
        raise ValueError(f"XIAO_YUN_START 仅支持 self 或 next，收到 {constants.XIAO_YUN_START!r}")
    qi_yun = chart.qi_yun or calculate_qi_yun(chart)
    birth_time = _local_naive(chart.birth.effective_time)
    forward = _is_forward_direction(chart.stems["year"], chart.birth.gender)
    step = 1 if forward else -1
    initial_offset = 0 if constants.XIAO_YUN_START == "self" else step
    term_shift_minutes = _term_shift_minutes(chart.birth)
    first_year = _lichun_year(birth_time, term_shift_minutes)
    last_year = _lichun_year(qi_yun.start_date, term_shift_minutes)
    cycles: list[XiaoYun] = []
    for year in range(first_year, last_year + 1):
        interval_start = _lichun_at(year, term_shift_minutes)
        interval_end = _lichun_at(year + 1, term_shift_minutes)
        if max(birth_time, interval_start) >= min(qi_yun.start_date, interval_end):
            continue
        offset = initial_offset + step * len(cycles)
        pillar = _advance_pillar(chart.pillars["hour"], offset)
        cycles.append(XiaoYun(
            year=year,
            pillar=pillar,
            stem=pillar[0],
            branch=pillar[1],
            stem_ten_god=ten_god(chart.day_master, pillar[0]),
            branch_ten_gods=_branch_ten_gods(chart.day_master, pillar[1]),
        ))
    chart.xiao_yun = cycles
    return cycles


def populate_fortune_cycles(
    chart: BaziChart,
    dayun_steps: int = 8,
    liunian_year_range: tuple[int, int] | None = None,
) -> BaziChart:
    """一次写入起运、大运和小运；流年仅在调用者给定范围时生成。"""
    calculate_qi_yun(chart)
    calculate_da_yun(chart, dayun_steps)
    calculate_xiao_yun(chart)
    if liunian_year_range is not None:
        calculate_liu_nian(chart, *liunian_year_range)
    return chart


def _is_forward_direction(year_stem: str, gender: str) -> bool:
    """阳年男、阴年女顺行；其余组合逆行。"""
    normalized_gender = gender.strip().lower()
    if normalized_gender in {"male", "男"}:
        male = True
    elif normalized_gender in {"female", "女"}:
        male = False
    else:
        raise ValueError(f"性别须为 male/female 或 男/女，收到 {gender!r}")
    _, polarity = STEM_PROPERTIES[year_stem]
    return (polarity == "yang") == male


def _target_jie(
    moment: datetime,
    forward: bool,
    *,
    term_shift_minutes: float = 0.0,
) -> tuple[str, datetime]:
    """从十二节中选择顺行的下一节或逆行的上一节。"""
    jie = [
        (name, at + timedelta(minutes=term_shift_minutes))
        for name, at in _jie_datetimes_around(moment)
    ]
    candidates = [(name, at) for name, at in jie if at > moment] if forward else [
        (name, at) for name, at in jie if at < moment
    ]
    if not candidates:
        raise ValueError(f"无法找到出生时刻 {moment.isoformat()} 的目标节")
    return min(candidates, key=lambda item: item[1]) if forward else max(candidates, key=lambda item: item[1])


def _jie_datetimes_around(moment: datetime) -> list[tuple[str, datetime]]:
    """从相邻三年的 lunar-python 节气表取十二节，并按时刻去重。"""
    results: dict[datetime, str] = {}
    for year in range(moment.year - 1, moment.year + 2):
        lunar = _to_lunar(datetime(year, 7, 1, 12, 0, 0))
        table = lunar.getJieQiTable()
        for raw_name in Lunar.JIE_QI_IN_USE[::2]:
            solar = table.get(raw_name)
            if solar is not None:
                results.setdefault(_solar_to_datetime(solar), JIE_DISPLAY_NAMES.get(raw_name, raw_name))
    return [(name, at) for at, name in results.items()]


def _qi_yun_age(elapsed_seconds: float) -> tuple[int, int, float]:
    """把到节的秒差折成起运年龄：一小时为五日，三百六十日为一年。"""
    fortune_days = elapsed_seconds / 3_600 * 5
    years, remainder = divmod(fortune_days, 360)
    months, days = divmod(remainder, 30)
    return int(years), int(months), days


def _add_calendar_duration(moment: datetime, years: int, months: int, days: float) -> datetime:
    """把折得的年、月、日加回出生时刻，日的小数保留到秒。"""
    year_delta, target_month_index = divmod(moment.month - 1 + months, 12)
    target_year = moment.year + years + year_delta
    target_month = target_month_index + 1
    target_day = min(moment.day, monthrange(target_year, target_month)[1])
    base = moment.replace(year=target_year, month=target_month, day=target_day)
    return base + timedelta(days=days)


def _advance_pillar(pillar: str, offset: int) -> str:
    """干支各按其固有周期推进，用于大运、小运的顺逆排列。"""
    return (
        STEMS[(STEMS.index(pillar[0]) + offset) % len(STEMS)]
        + BRANCHES[(BRANCHES.index(pillar[1]) + offset) % len(BRANCHES)]
    )


def _branch_ten_gods(day_master: str, branch: str) -> list[str]:
    """地支十神以其唯一来源中的全部非空藏干列示。"""
    return [
        ten_god(day_master, stem)
        for stem in constants.hidden_stems_of(branch).values()
        if stem is not None
    ]


def _year_pillar_at_lichun(year: int) -> str:
    """取立春后该公历年的年柱，避免按元旦直接换年。"""
    lichun = _lichun_at(year)
    return _to_lunar(lichun + timedelta(seconds=1)).getYearInGanZhiExact()


def _lichun_year(moment: datetime, term_shift_minutes: float = 0.0) -> int:
    """返回该时刻所属的立春年份标签。"""
    return moment.year if moment >= _lichun_at(moment.year, term_shift_minutes) else moment.year - 1


def _lichun_at(year: int, term_shift_minutes: float = 0.0) -> datetime:
    """从 lunar-python 节气表取指定公历年的立春精确时刻。"""
    candidates = [
        at for name, at in _jie_datetimes_around(datetime(year, 7, 1, 12, 0, 0))
        if name == "立春" and at.year == year
    ]
    if len(candidates) != 1:
        raise ValueError(f"无法唯一确定 {year} 年立春时刻")
    return candidates[0] + timedelta(minutes=term_shift_minutes)


def ten_god(day_master: str, stem: str) -> str:
    """以日主为我，计算任一天干的十神。"""
    day_element, day_polarity = STEM_PROPERTIES[day_master]
    element, polarity = STEM_PROPERTIES[stem]
    same_polarity = polarity == day_polarity
    if element == day_element:
        return "比肩" if same_polarity else "劫财"
    if PRODUCES[element] == day_element:
        return "偏印" if same_polarity else "正印"
    if PRODUCES[day_element] == element:
        return "食神" if same_polarity else "伤官"
    if CONTROLS[day_element] == element:
        return "偏财" if same_polarity else "正财"
    if CONTROLS[element] == day_element:
        return "七杀" if same_polarity else "正官"
    raise ValueError(f"无法计算日主 {day_master} 与天干 {stem} 的十神")


def populate_shi_shen(chart: BaziChart) -> None:
    """为四柱天干和全部非空藏干写入位置 ID 到十神名的映射。"""
    shi_shen: dict[str, str] = {}
    for pillar in PILLAR_NAMES:
        shi_shen[ids.bz_stem(pillar)] = ten_god(chart.day_master, chart.stems[pillar])
        for layer in HIDDEN_STEM_LAYERS:
            stem = chart.hidden_stems[pillar][layer]
            if stem is not None:
                shi_shen[ids.bz_hidden(pillar, layer)] = ten_god(chart.day_master, stem)
    chart.shi_shen = shi_shen


def analyze(chart: BaziChart) -> list[Evidence]:
    """先固化取格事实；成败规则未覆盖时只降级该层。"""
    populate_shi_shen(chart)
    chart.ge_ju_assessment = {
        "version": PATTERN_RULE_VERSION, "state": "grid_pending",
        "method": "month_grid", "basis": [], "conditions": [],
    }
    decision = _determine_grid(chart)
    chart.ge_ju_resolution_status = decision.status
    chart.ge_ju_candidates = list(decision.candidates)
    if decision.status is not GeJuResolutionStatus.RESOLVED:
        refs = list(decision.refs)
        chart.ge_ju = None
        chart.ge_ju_status = None
        chart.ge_ju_clarity = None
        chart.ge_ju_variant = None
        chart.ge_ju_god = None
        chart.ge_ju_yong_shen = None
        chart.xiang_shen = None
        chart.xiang_shen_resolution_status = XiangShenResolutionStatus.UNRESOLVED
        chart.ge_ju_unavailable_reason = decision.reason
        # An unresolved scope boundary is not counted as completed adjudication.
        chart.ge_ju_assessment.update({
            "state": "scope_boundary" if decision.candidates else "implementation_gap",
            "boundary_code": "month_peer_unexposed_candidates" if decision.candidates else "missing_month_rule",
            "conditions": [decision.reason],
            "basis": [item.basis for item in decision.candidates],
        })
        alternatives = []
        for candidate in decision.candidates:
            alternative = replace(chart, ge_ju=candidate.grid, ge_ju_god=candidate.god)
            candidate_status, candidate_xiang, _ = _evaluate_grid_variant(
                alternative, [candidate.god.id], "杂气候选条件评估")
            alternatives.append({
                "grid": candidate.grid, "grid_ref": candidate.god.id,
                "hypothetical": True, "status": candidate_status,
                "xiang": asdict(_build_xiang_shen(alternative, candidate_xiang))
                if candidate_xiang else None,
                "assessment": alternative.ge_ju_assessment,
            })
        chart.ge_ju_assessment["alternatives"] = alternatives
        candidate_names = "、".join(item.grid for item in decision.candidates)
        return [Evidence(
            system=System.BAZI,
            claim=(
                f"月令司令已确定，仅保留{candidate_names}候选，未定格"
                if candidate_names else
                "月令司令已确定，取格暂不裁决"
            ),
            refs=refs,
            polarity=Polarity.NEUTRAL,
            weight=_evidence_weight(refs),
            source="子平真诠·月令取格原则",
        )]
    grid = decision.grid
    assert grid is not None
    candidate_refs = list(decision.refs)
    chart.ge_ju = grid
    chart.ge_ju_clarity = decision.clarity
    chart.ge_ju_variant = None
    chart.ge_ju_god = _build_ge_ju_god(chart, grid, candidate_refs)
    source = f"子平真诠·{grid}成败"
    grid_evidence = Evidence(
        system=System.BAZI,
        claim=f"月令取 {grid}",
        refs=candidate_refs,
        polarity=Polarity.NEUTRAL,
        weight=_evidence_weight(candidate_refs),
        source=source,
    )
    try:
        status, xiang_shen_id, status_evidence = _evaluate_grid(
            chart,
            candidate_refs,
            source,
        )
    except NotImplementedError:
        chart.ge_ju_status = None
        chart.ge_ju_yong_shen = None
        chart.xiang_shen = None
        chart.xiang_shen_resolution_status = XiangShenResolutionStatus.UNRESOLVED
        chart.ge_ju_unavailable_reason = f"{grid}成败规则尚未纳入当前版本"
        return [grid_evidence, Evidence(
            system=System.BAZI,
            claim=f"{grid}已定格，成败与相神暂不裁决",
            refs=candidate_refs,
            polarity=Polarity.NEUTRAL,
            weight=_evidence_weight(candidate_refs),
            source=source,
        )]

    chart.ge_ju_status = status
    if status is None:
        chart.ge_ju_yong_shen = None
        chart.xiang_shen = None
        chart.xiang_shen_resolution_status = XiangShenResolutionStatus.UNRESOLVED
        chart.ge_ju_unavailable_reason = "；".join(chart.ge_ju_assessment["conditions"])
        return [grid_evidence, *status_evidence]
    chart.xiang_shen = _build_xiang_shen(chart, xiang_shen_id)
    chart.xiang_shen_resolution_status = (
        XiangShenResolutionStatus.RESOLVED
        if chart.xiang_shen is not None else
        XiangShenResolutionStatus.ABSENT
    )
    chart.ge_ju_yong_shen = _build_ge_ju_yong_shen(chart)
    chart.ge_ju_unavailable_reason = None
    evidence = [grid_evidence, *status_evidence]
    yong_shen = chart.ge_ju_yong_shen
    if yong_shen is not None:
        yong_refs = list(candidate_refs)
        god_names = "、".join(yong_shen.ten_gods)
        if yong_shen.primary is not None:
            yong_refs.append(yong_shen.primary.id)
        evidence.append(Evidence(
            system=System.BAZI,
            claim=(
                f"格局派用神按{yong_shen.principle}取{god_names}"
                + (
                    f"，盘面主用为{yong_shen.primary.stem}（{yong_shen.primary.ten_god}）"
                    if yong_shen.primary is not None else
                    "，盘面暂未收敛到单一主用位置"
                )
            ),
            refs=_unique(yong_refs)[:4],
            polarity=Polarity.NEUTRAL,
            weight=_evidence_weight(_unique(yong_refs)[:4]),
            source=source,
        ))
    if decision.clarity == "暗格":
        evidence.append(Evidence(
            system=System.BAZI,
            claim="暗格保留藏干取格标记，不以加权分数代替成败条件",
            refs=candidate_refs,
            polarity=Polarity.NEUTRAL,
            weight=_evidence_weight(candidate_refs),
            source=source,
        ))
    return evidence




def _grid_unavailable_reason(error: NotImplementedError) -> str:
    """共享排盘入口的显式降级接口；未知规则仍须暴露，不能吞成已决结果。"""
    message = str(error).removesuffix("尚未纳入 v1")
    return f"{message}尚未纳入当前版本" if message else "当前版本尚未覆盖该格局"


@dataclass(frozen=True)
class _GridDecision:
    status: GeJuResolutionStatus
    grid: str | None
    refs: tuple[str, ...]
    clarity: str | None = None
    candidates: tuple[GeJuCandidate, ...] = ()
    reason: str | None = None


def _resolved_grid(grid: str, refs: list[str], clarity: str | None = None) -> _GridDecision:
    return _GridDecision(GeJuResolutionStatus.RESOLVED, grid, tuple(refs), clarity)


def _determine_grid(chart: BaziChart) -> _GridDecision:
    """按司令透出、月令藏干、禄刃、暗格的优先级定格。"""
    if not chart.siling:
        raise ValueError("月令司令为空，无法定格")

    exposed = _stem_locations(chart, chart.siling)
    if (
        exposed
        and ten_god(chart.day_master, chart.siling) not in {"比肩", "劫财"}
        and not _only_day_master_exposed(chart, exposed, chart.siling)
    ):
        grid = _grid_for_stem(chart, chart.siling)
        return _resolved_grid(grid, [_siling_reference(chart), *exposed])

    candidates = _hidden_candidates(chart)
    if candidates:
        selected = max(candidates, key=lambda candidate: candidate[0])
        _, stem, refs = selected
        return _resolved_grid(_grid_for_stem(chart, stem), refs)

    month_branch = chart.branches["month"]
    if month_branch == LU_TABLE[chart.day_master]:
        return _resolved_grid("建禄格", [
            ids.bz_branch("month"),
            _month_hidden_ten_god_reference(chart, "比肩"),
        ])
    if month_branch == REN_TABLE.get(chart.day_master):
        return _resolved_grid("阳刃格", [
            ids.bz_branch("month"),
            _month_hidden_ten_god_reference(chart, "劫财"),
        ])

    month_benqi = chart.hidden_stems["month"]["benqi"]
    if month_benqi and ten_god(chart.day_master, month_benqi) == "劫财":
        return _resolved_grid("月劫格", [ids.bz_hidden("month", "benqi")])

    if (
        month_benqi
        and ten_god(chart.day_master, chart.siling) in {"比肩", "劫财"}
        and ten_god(chart.day_master, month_benqi) not in {"比肩", "劫财"}
    ):
        return _resolved_grid(
            _grid_for_stem(chart, month_benqi),
            [ids.bz_hidden("month", "benqi")],
            "暗格",
        )

    if ten_god(chart.day_master, chart.siling) in {"比肩", "劫财"}:
        candidates = _unresolved_month_grid_candidates(chart)
        refs = [_siling_reference(chart), *(item.god.id for item in candidates)]
        status = (
            GeJuResolutionStatus.CANDIDATES
            if candidates else
            GeJuResolutionStatus.RULE_UNAVAILABLE
        )
        return _GridDecision(
            status=status,
            grid=None,
            refs=tuple(_unique(refs)),
            candidates=tuple(candidates),
            reason=(
                f"{ten_god(chart.day_master, chart.siling)}司令，月令非比劫藏干未达到透会定格条件"
                if candidates else
                f"{ten_god(chart.day_master, chart.siling)}司令取格规则尚未覆盖"
            ),
        )

    return _resolved_grid(
        _grid_for_stem(chart, chart.siling),
        [_siling_reference(chart)],
        "暗格",
    )


def _unresolved_month_grid_candidates(chart: BaziChart) -> list[GeJuCandidate]:
    """保留未透会的非比劫月令藏干；只列候选，不越权定格。"""
    labels = {"benqi": "本气", "zhongqi": "中气", "yuqi": "余气"}
    candidates: list[GeJuCandidate] = []
    for layer in HIDDEN_STEM_LAYERS:
        stem = chart.hidden_stems["month"][layer]
        if stem is None or ten_god(chart.day_master, stem) in {"比肩", "劫财"}:
            continue
        element_id = ids.bz_hidden("month", layer)
        god = ten_god(chart.day_master, stem)
        candidates.append(GeJuCandidate(
            grid=_grid_for_stem(chart, stem),
            god=GeJuGod(id=element_id, stem=stem, ten_god=god),
            basis=f"月令{labels[layer]}藏干未透且未成会局",
        ))
    return candidates


def _month_hidden_ten_god_reference(chart: BaziChart, target: str) -> str:
    """取得禄刃在月支藏干中的定格位置，不借用当段司令。"""
    for layer in HIDDEN_STEM_LAYERS:
        stem = chart.hidden_stems["month"][layer]
        if stem is not None and ten_god(chart.day_master, stem) == target:
            return ids.bz_hidden("month", layer)
    raise ValueError(f"月支 {chart.branches['month']} 中找不到 {target} 格神")


def _siling_reference(chart: BaziChart) -> str:
    """将当段司令映射回月令藏干的实际盘面位置。"""
    for layer in HIDDEN_STEM_LAYERS:
        if chart.hidden_stems["month"][layer] == chart.siling:
            return ids.bz_hidden("month", layer)
    # 合成规则测试可只提供司令透干；此时仍引用实际透干位置而非虚拟 ID。
    exposed = _stem_locations(chart, chart.siling)
    if exposed:
        return exposed[0]
    raise ValueError(f"月令司令 {chart.siling} 不在月令藏干中且未透出")


def _grid_for_stem(chart: BaziChart, stem: str) -> str:
    """将非比劫候选天干转换为八格名称。"""
    ten_god_name = ten_god(chart.day_master, stem)
    grid = GRID_BY_TEN_GOD.get(ten_god_name)
    if grid is None:
        raise NotImplementedError(f"{ten_god_name}司令取格尚未纳入 v1")
    return grid


def _only_day_master_exposed(chart: BaziChart, refs: list[str], stem: str) -> bool:
    """判断司令仅透日主自身；该情形须进入后续优先级而非以比劫取格。"""
    return stem == chart.day_master and refs == [ids.bz_stem("day")]


def _hidden_candidates(chart: BaziChart) -> list[tuple[tuple[int, int, int], str, list[str]]]:
    """取得月令藏干中透出或成会局的候选，并按规定优先级编码排序。"""
    candidates: list[tuple[tuple[int, int, int], str, list[str]]] = []
    layer_priority = {"benqi": 3, "zhongqi": 2, "yuqi": 1}
    for layer, priority in layer_priority.items():
        stem = chart.hidden_stems["month"][layer]
        if stem is None or ten_god(chart.day_master, stem) in {"比肩", "劫财"}:
            continue
        exposed = _stem_locations(chart, stem)
        combination_refs = _combination_refs(chart, STEM_PROPERTIES[stem][0])
        if not exposed and not combination_refs:
            continue
        refs = [ids.bz_hidden("month", layer), *exposed, *combination_refs]
        root_strength = _root_strength(chart, stem)
        rank = (1 if combination_refs else 0, priority, root_strength)
        candidates.append((rank, stem, _unique(refs)))
    return candidates


def _stem_locations(chart: BaziChart, stem: str) -> list[str]:
    """取得某天干透出的所有位置 ID。"""
    return [
        ids.bz_stem(pillar)
        for pillar in PILLAR_NAMES
        if chart.stems[pillar] == stem
    ]


def _combination_refs(chart: BaziChart, element: str) -> list[str]:
    """返回与候选天干五行一致的三合、三会（或配置允许的半合）证据。"""
    available = set(chart.branches.values())
    refs: list[str] = []
    for group, group_element in (*THREE_COMBINATIONS, *THREE_MEETINGS):
        if group_element != element:
            continue
        matched = group & available
        complete = group <= available
        partial = constants.HALF_COMBINATION_COUNTS and len(matched) == 2
        if complete or partial:
            refs.extend(
                ids.bz_branch(pillar)
                for pillar in PILLAR_NAMES
                if chart.branches[pillar] in matched
            )
    return _unique(refs)


def _root_strength(chart: BaziChart, stem: str) -> int:
    """以全盘藏干出现次数作为同层候选的通根强度。"""
    return sum(
        hidden == stem
        for layers in chart.hidden_stems.values()
        for hidden in layers.values()
    )
def _evaluate_grid(chart, grid_refs, source):
    """All registered grids use the same path → damage → rescue adjudicator."""
    if chart.ge_ju not in EVALUATED_GRIDS:
        raise AssertionError(f"格局缺少注册处理器：{chart.ge_ju}")
    return _evaluate_grid_variant(chart, grid_refs, source)


def _pattern_combinations(chart: BaziChart) -> dict[str, str]:
    """合绊非化气：近合优先、阻隔不合、争合不去、日主本身之合不去。

    隔一柱允许无克阻的合；年时遥合不当作完全合去。只接受互为唯一最近
    对象的配对，不能把一个干同时分配给两个救应者。详见规则说明。
    """
    stems = {ids.bz_stem(p): s for p, s in chart.stems.items()}
    order = {ids.bz_stem(p): i for i, p in enumerate(PILLAR_NAMES)}
    choices = {}
    for left, a in stems.items():
        pairs = []
        for right, b in stems.items():
            if right == left or frozenset({a, b}) not in STEM_COMBINATIONS:
                continue
            distance = abs(order[left] - order[right])
            if distance > 2:
                continue
            lo, hi = sorted((order[left], order[right]))
            blocked = any(
                lo < order[mid] < hi and
                CONTROLS[STEM_PROPERTIES[s][0]] in {STEM_PROPERTIES[a][0], STEM_PROPERTIES[b][0]}
                for mid, s in stems.items()
            )
            if not blocked:
                pairs.append((distance, right))
        if pairs:
            near = min(distance for distance, _ in pairs)
            candidates = [right for distance, right in pairs if distance == near]
            if len(candidates) == 1:
                choices[left] = candidates[0]
    return {left: right for left, right in choices.items() if choices.get(right) == left
            and ids.bz_stem("day") not in {left, right}}


def _pattern_reaches(chart, left, right):
    """作用位置口径：同柱或相隔至多一柱；不穿越克制施事者的天干。"""
    a, b = left.split(".")[2], right.split(".")[2]
    lo, hi = sorted((PILLAR_NAMES.index(a), PILLAR_NAMES.index(b)))
    if hi - lo > 2:
        return False
    stem = _all_stem_locations(chart)[left][0]
    return not any(
        CONTROLS[STEM_PROPERTIES[chart.stems[PILLAR_NAMES[i]]][0]] == STEM_PROPERTIES[stem][0]
        for i in range(lo + 1, hi)
    )


def _month_branch_damage(chart):
    """官格月令的冲、害与完整刑局；六合解救须有第三位置且救者不再逢冲。"""
    month, branches = chart.branches["month"], set(chart.branches.values())
    punishments = (frozenset({"子", "卯"}), frozenset({"寅", "巳", "申"}), frozenset({"丑", "戌", "未"}))
    result = {}
    for pillar, branch in chart.branches.items():
        if pillar == "month":
            continue
        pair = frozenset({month, branch})
        harmed = pair in (*constants.BRANCH_SIX_CLASHES, *constants.BRANCH_SIX_HARMS)
        harmed = harmed or any(pair <= group <= branches and len(pair) > 1 for group in punishments)
        if not harmed:
            continue
        rescuers = [ids.bz_branch(other) for other, partner in chart.branches.items()
                    if other not in {"month", pillar}
                    and any(frozenset({partner, target}) in constants.BRANCH_SIX_COMBINATIONS for target in pair)
                    and not any(frozenset({partner, b}) in constants.BRANCH_SIX_CLASHES for b in branches)]
        result[ids.bz_branch(pillar)] = rescuers
    return result


def _evaluate_grid_variant(chart, grid_refs, source):
    """Finite, versioned common-grid policy; failed prerequisites are not unknowns.

    Every candidate is evaluated. A successful route does not excuse its damage,
    and a failed route does not prevent a different route from succeeding.
    """
    assert chart.ge_ju in EVALUATED_GRIDS
    groups = {
        "官": frozenset({"正官"}), "杀": frozenset({"七杀"}),
        "财": frozenset({"正财", "偏财"}), "印": frozenset({"正印", "偏印"}),
        "食伤": frozenset({"食神", "伤官"}), "比劫": frozenset({"比肩", "劫财"}),
    }
    positions = _all_stem_locations(chart)
    raw = {key: _exposed_locations_by_ten_god(chart, names) for key, names in groups.items()}
    combined = _pattern_combinations(chart)
    live = {key: {ref: value for ref, value in values.items() if ref not in combined}
            for key, values in raw.items()}
    features = {key: _pattern_strength(chart, names) for key, names in groups.items()}
    bodies = features["比劫"]
    body_strong = bodies["strong"] or (bodies["main_roots"] >= 1 and features["印"]["strong"])
    body_weak = bodies["main_roots"] == 0 and bodies["roots"] <= 1
    seal_strong, output_strong = features["印"]["strong"], features["食伤"]["strong"]

    def rooted(ref):
        element = STEM_PROPERTIES[positions[ref][0]][0]
        return any(s and STEM_PROPERTIES[s][0] == element
                   for hidden in chart.hidden_stems.values() for s in hidden.values())

    def controls(left, right):
        return (left != right and _pattern_reaches(chart, left, right)
                and CONTROLS[STEM_PROPERTIES[positions[left][0]][0]] == STEM_PROPERTIES[positions[right][0]][0])

    active_stems = {ref: value for values in live.values() for ref, value in values.items()}

    def powered(ref):
        # 食伤不必只有本气根：有根比劫透出相生也可承接（乙亥乙酉乙卯丁丑）。
        element = STEM_PROPERTIES[positions[ref][0]][0]
        return rooted(ref) or any(rooted(parent) and _pattern_reaches(chart, parent, ref)
                                 and PRODUCES[STEM_PROPERTIES[value[0]][0]] == element
                                 for parent, value in active_stems.items() if parent != ref)

    def usable(ref, trail=frozenset()):
        if ref in combined or ref in trail or not powered(ref):
            return False
        # A rescuer may itself be rescued. A cyclic chain is not proof of rescue.
        return not any(controls(attacker, ref) and usable(attacker, trail | {ref})
                       for attacker in active_stems if attacker not in trail)

    def hidden_role(key):
        # 藏干不得视为全部透出：只取本气、月令，或同气已成会局的位置。
        return {ref: value for ref, value in positions.items()
                if ref.startswith("bz.hidden.") and chart.shi_shen[ref] in groups[key]
                and (ref.endswith(".benqi") or ref.startswith("bz.hidden.month.")
                     or features[key]["assembly"])}

    role = {key: dict(value) for key, value in live.items()}
    auxiliary_keys = {
        "正印格": ("官", "杀", "财", "食伤"), "偏印格": ("官", "杀", "财", "食伤"),
        "伤官格": ("官", "杀", "财", "印"),
        "建禄格": ("官", "杀", "财", "食伤"), "月劫格": ("官", "杀", "财", "食伤"),
        "阳刃格": ("官", "杀"),
    }.get(chart.ge_ju, ())
    if auxiliary_keys and not any(raw[key] for key in auxiliary_keys):
        for key in auxiliary_keys:
            role[key] = hidden_role(key)
    # 禄劫可借支中会局转劫生财、制杀；半会仅用于辅用，不改变透会取格开关。
    output_assembly = {}
    branches = set(chart.branches.values())
    for group, element in THREE_COMBINATIONS:
        matched = group & branches
        if len(matched) >= 2 and matched & {"子", "午", "卯", "酉"}:
            if any(pair <= branches and pair & matched for pair in constants.BRANCH_SIX_CLASHES):
                continue
            output_assembly.update({
                ref: value for ref, value in positions.items()
                if ref.startswith("bz.hidden.") and chart.shi_shen[ref] in groups["食伤"]
                and STEM_PROPERTIES[value[0]][0] == element
                and chart.branches[ref.split(".")[2]] in matched
            })
    if chart.ge_ju in {"建禄格", "月劫格"} and not role["食伤"]:
        role["食伤"] = output_assembly
    clearings = {}
    if live["官"] and live["杀"]:
        for remove, keep in (("杀", "官"), ("官", "杀")):
            selective = {
                target: [ref for ref in live["食伤"] if usable(ref) and controls(ref, target)
                         and not any(controls(ref, other) for other in live[keep])]
                for target in live[remove]
            }
            if selective and all(selective.values()):
                clearings.update(selective)
                role[remove] = {}
                break
    official, killing, wealth, seal, output, peers = (role[key] for key in groups)
    raw_o, raw_k, raw_w, raw_i, raw_e, raw_p = (raw[key] for key in groups)
    hurting = {ref: value for ref, value in raw_e.items() if chart.shi_shen[ref] == "伤官"}
    mixed = bool(role["官"] and role["杀"] and live["官"] and live["杀"])
    paths, failures = [], []
    transit_damage = {}
    branch_damage = _month_branch_damage(chart) if chart.ge_ju == "正官格" else {}

    def check(code, passed, label, refs=()):
        return {"code": code, "passed": bool(passed), "label": label, "refs": list(refs)}

    def add(name, decisive, checks=(), damage=None, helpers=None, *, rescue=False, grade="常格",
            combine_restraint=False, transform_peers=False, damage_ten_gods=frozenset()):
        damage, helpers = {**(damage or {}), **dict.fromkeys(branch_damage)}, helpers or {}
        checks = [check("auxiliary_present", decisive, "有实际辅用位置", decisive),
                  check("officer_killing_clear", not mixed or chart.ge_ju == "食神格", "官杀取清（食神格并见只降等）", [*live["官"], *live["杀"]]),
                  *checks]
        unresolved, rescues = [], {}
        for target in damage:
            if target in branch_damage:
                if branch_damage[target]:
                    rescues[target] = branch_damage[target]
                else:
                    unresolved.append(target)
            elif target in combined:
                rescues[target] = [combined[target]]
            elif target in clearings:
                rescues[target] = clearings[target]
            else:
                saviors = [ref for ref in helpers if usable(ref) and (
                    controls(ref, target) or (
                        transform_peers and target in raw_p and ref in output
                        and _pattern_reaches(chart, target, ref)
                        and PRODUCES[STEM_PROPERTIES[positions[target][0]][0]] == STEM_PROPERTIES[positions[ref][0]][0]
                    ))]
                if saviors:
                    rescues[target] = saviors
                else:
                    unresolved.append(target)
        path = {"name": name, "checks": checks, "decisive": list(decisive),
                "damage": list(damage), "rescues": rescues, "unresolved_damage": unresolved,
                "grade": grade, "outcome": "rejected"}
        if all(item["passed"] for item in checks):
            path["outcome"] = "成中有败" if unresolved else (
                "败中有救" if rescues or rescue else "成格")
            # Rescuers, not merely the usual supportive god, become decisive.
            path["xiang"] = list(dict.fromkeys(
                [ref for refs in rescues.values() for ref in refs] + list(decisive)
            ))
            path["xiang"] = [ref for ref in path["xiang"]
                            if ref in positions and (combine_restraint or ref not in combined
                            or ref in {r for rs in rescues.values() for r in rs})]
        else:
            path["xiang"] = []
        paths.append(path)
        # Transit categories include potential attackers absent from the natal chart.
        # Keep this metadata separate so existing path evidence is unchanged.
        transit_damage[name] = damage_ten_gods

    def fail(code, matched, label, refs):
        names = {"mixed_unresolved": "官杀混杂未清", "hurting_officer": "伤官见官",
                 "seal_light_wealth_heavy": "财破印", "body_seal_excess_killing": "印重逢杀",
                 "seal_light_output_heavy": "印浅泄重", "wearing_seal_excess": "身旺伤轻佩印",
                 "wealth_killing_body_weak": "财杀身轻", "lu_killing_uncontrolled": "禄劫杀无制",
                 "blade_no_control": "阳刃缺少制化", "officer_hurt": "官逢伤克",
                 "officer_branch_damage": "官根刑冲害",
                 "wealth_light_peer_heavy": "财轻比重", "wealth_feeds_killing": "财党杀",
                 "food_owl": "枭夺食", "food_wealth_killing": "食财带杀",
                 "killing_wealth_no_control": "财生杀无制"}
        failures.append({"code": code, "matched": bool(matched), "name": names[code], "label": label, "refs": list(refs)})

    strong = check("body_supported", body_strong, "日主有承受泄耗的根气", features["比劫"]["root_refs"])
    seal_root = check("seal_rooted", features["印"]["roots"], "印有根", features["印"]["root_refs"])
    output_root = check("output_rooted", features["食伤"]["roots"] or any(powered(ref) for ref in output),
                        "食伤有根或有根生源承接", [*features["食伤"]["root_refs"], *output])
    wealth_root = check("wealth_rooted", features["财"]["roots"], "财有根", features["财"]["root_refs"])
    control_root = check("control_rooted", any(rooted(ref) for ref in (official or killing)), "制约者有根", [*official, *killing])
    seal_attacks_output = {ref: value for ref, value in raw_i.items()
                           if any(controls(ref, target) for target in output)}
    wealth_attacks_seal = {ref: value for ref, value in raw_w.items()
                          if any(controls(ref, target) for target in seal)}
    fail("mixed_unresolved", mixed and chart.ge_ju != "食神格", "官杀竞出而未合去取清", [*live["官"], *live["杀"]])

    if chart.ge_ju in {"正印格", "偏印格"}:
        add("官印双全", official, (seal_root,), {**wealth_attacks_seal, **hurting}, {**seal, **peers},
            damage_ten_gods=groups["财"] | frozenset({"伤官"}))
        add("印格杀逢食制", output,
            (check("killing_present", killing, "有七杀", killing), output_root),
            {**raw_w, **seal_attacks_output}, peers,
            damage_ten_gods=groups["财"] | groups["印"])
        add("印用七杀", killing, (seal_root, check("not_body_seal_excess", not (body_strong and seal_strong),
                                               "非身印俱旺又增杀")),
            wealth_attacks_seal, peers,
            damage_ten_gods=groups["财"])
        # 印多财轻以财裁印，不把财印相合直接等同财失用（论印·辛酉丙申壬申辛亥）。
        add("印多用财", raw_w,
            (strong, check("seal_abundant", seal_strong, "印旺", features["印"]["root_refs"]),
             check("wealth_light", not features["财"]["strong"], "财透根轻")),
            raw_e, seal, combine_restraint=True,
            damage_ten_gods=groups["食伤"])
        add("印用食伤", output,
            (strong, check("seal_abundant", seal_strong, "印旺", features["印"]["root_refs"])),
            raw_w, peers,
            damage_ten_gods=groups["财"])
        if raw_w and not seal_strong:
            add("印逢财而比劫护印", peers, (seal_root,), raw_w, peers, rescue=True,
                damage_ten_gods=groups["财"])
        fail("seal_light_wealth_heavy", not seal_strong and bool(live["财"]),
             "印轻逢财，破印路径存在", live["财"])
        fail("body_seal_excess_killing", body_strong and seal_strong and bool(live["杀"]),
             "身强印重再透杀", live["杀"])
        fail("seal_light_output_heavy", body_weak and not seal_strong and output_strong and bool(output),
             "印浅身轻又逢重泄", output)

    elif chart.ge_ju == "伤官格":
        add("伤官生财", wealth, (strong, wealth_root), {**raw_k, **raw_o}, {**output, **seal},
            damage_ten_gods=groups["杀"] | groups["官"])
        add("伤官佩印", seal,
            (seal_root, check("output_strong", output_strong, "伤官有力"),
             check("body_not_excess", not body_strong, "非身旺伤轻")),
            wealth_attacks_seal, peers,
            damage_ten_gods=groups["财"])
        add("伤官财印并用", {**wealth, **seal},
            (check("both_present", wealth and seal, "财印俱有实际位置", [*wealth, *seal]),
             check("wealth_or_seal_rooted", features["财"]["roots"] or features["印"]["roots"],
                   "财印至少一端有根，分任生财与扶身", [*features["财"]["root_refs"], *features["印"]["root_refs"]]),
             check("wealth_seal_separated", not wealth_attacks_seal, "财印位置不相碍", [*wealth, *seal])),
            {**raw_k, **raw_o}, output,
            damage_ten_gods=groups["杀"] | groups["官"])
        add("伤官用杀印", seal,
            (check("killing_present", killing, "有七杀", killing),
             check("body_weak", body_weak, "身弱可用杀印"), seal_root),
            wealth_attacks_seal, peers,
            damage_ten_gods=groups["财"])
        month_output = {ref: positions[ref] for ref in grid_refs
                        if ref in positions and chart.shi_shen[ref] in groups["食伤"]}
        add("伤官驾杀", output or month_output,
            (check("killing_present", killing, "有七杀", killing),
             check("output_strong", output_strong, "伤官有力"),
             check("body_not_weak", not body_weak, "日主非无承受之根")),
            {**raw_w, **seal_attacks_output}, peers,
            damage_ten_gods=groups["财"] | groups["印"])
        winter_metal = (STEM_PROPERTIES[chart.day_master][0] == "metal"
                        and STEM_PROPERTIES[chart.siling][0] == "water"
                        and chart.branches["month"] in {"亥", "子", "丑"})
        add("金水伤官用官", official,
            (check("winter_metal", winter_metal, "冬月金水伤官"),
             check("wealth_or_seal", wealth or seal, "财印相辅", [*wealth, *seal]), control_root,
             check("output_not_exposed", not live["食伤"], "伤官未与官同时透出", live["食伤"])),
            {}, {},
            damage_ten_gods=frozenset())
        if official:
            add("伤官见官而印制伤", seal, (seal_root, check("hurting_exposed", raw_e, "透伤可制", raw_e)),
                {**raw_e, **wealth_attacks_seal}, {**seal, **peers}, rescue=True,
                damage_ten_gods=groups["食伤"] | groups["财"])
            add("伤官见官而财通关", wealth, (strong, wealth_root,
                check("seal_not_hurt", not wealth_attacks_seal, "财不破护官之印"),
                check("wealth_bridge", any(usable(ref) and any(_pattern_reaches(chart, ref, o) for o in official)
                    and any(_pattern_reaches(chart, e, ref) for e in (output or month_output)) for ref in wealth),
                    "财有实际作用位置承接伤官并生官", [*wealth, *official])),
                raw_k, output, rescue=True,
                damage_ten_gods=groups["杀"])
        fail("hurting_officer", bool(live["官"]) and (not winter_metal or bool(live["食伤"])),
             "伤官见官且未满足金水用官条件", [*live["官"], *live["食伤"]])
        fail("wearing_seal_excess", bool(seal) and body_strong and not output_strong,
             "佩印而伤轻身旺", seal)
        fail("wealth_killing_body_weak", bool(wealth and killing) and body_weak,
             "生财带杀而身轻", [*wealth, *killing])

    elif chart.ge_ju in {"建禄格", "月劫格"}:
        add("禄劫用官", official, (control_root,),
            {**hurting, **raw_k}, seal, grade="财印辅助" if wealth or seal else "孤官无辅",
            damage_ten_gods=frozenset({"伤官"}) | groups["杀"])
        add("禄劫用杀", output,
            (check("killing_present", killing, "有七杀", killing), output_root),
            {**raw_w, **seal_attacks_output}, peers,
            damage_ten_gods=groups["财"] | groups["印"])
        add("禄劫用财", output,
            (check("wealth_present", wealth, "有财", wealth), output_root),
            {**raw_k, **seal_attacks_output}, {**peers, **output},
            damage_ten_gods=groups["杀"] | groups["印"])
        add("禄劫独财根深", wealth,
            (check("single_wealth", len(live["财"]) == 1, "财独透而不杂", live["财"]),
             check("wealth_deep", features["财"]["roots"] >= 2, "财有多支根气", features["财"]["root_refs"]),
             check("output_absent", not output, "不与财食路径重复")),
            {**raw_k, **raw_p}, official, grade="不等同财食相随",
            damage_ten_gods=groups["杀"] | groups["比劫"])
        add("禄劫泄秀", output,
            (output_root, check("no_control_or_wealth", not (official or killing or wealth), "无财官杀另取")),
            seal_attacks_output, wealth,
            damage_ten_gods=groups["印"])
        fail("lu_killing_uncontrolled", bool(killing) and not output and not (wealth or official),
             "禄劫透杀而无制伏", killing)

    elif chart.ge_ju == "阳刃格":
        add("阳刃用官" if official else "阳刃驾杀", official or killing, (control_root,),
            {**raw_e, **{ref: value for ref, value in (raw_o or raw_k).items() if ref in combined}},
            seal, grade="透干" if raw_o or raw_k else "官杀藏支",
            damage_ten_gods=groups["食伤"] | groups["官" if raw_o else "杀"])
        add("阳刃杀重食制", output,
            (check("killing_present", killing, "有七杀", killing), output_root,
             check("killing_heavy", features["杀"]["main_roots"] >= 2, "杀有多处本气强根")),
            {**raw_w, **seal_attacks_output}, peers,
            damage_ten_gods=groups["财"] | groups["印"])
        add("阳刃食伤生财", output,
            (check("wealth_present", wealth, "有财", wealth), wealth_root, output_root,
             check("no_control", not (official or killing), "无官杀另取")),
            seal_attacks_output, wealth,
            damage_ten_gods=groups["印"])
        fail("blade_no_control", not (official or killing or (wealth and output)),
             "阳刃无官杀制约亦无食伤生财", grid_refs)

    elif chart.ge_ju == "正官格":
        add("财生官", wealth, (), {**hurting, **raw_k}, seal,
            damage_ten_gods=frozenset({"伤官"}) | groups["杀"])
        add("印护官", seal, (seal_root,), {**hurting, **raw_k, **wealth_attacks_seal}, {**seal, **peers},
            damage_ten_gods=frozenset({"伤官"}) | groups["杀"] | groups["财"])
        # 清官无辅可保格，但不借格神冒充相神。
        fail("officer_hurt", bool(hurting), "正官逢伤", hurting)
        fail("officer_branch_damage", any(not refs for refs in branch_damage.values()), "官格月令逢刑冲害而未获有效合解", branch_damage)
        if not (wealth or seal or hurting or raw_k):
            paths.append({"name": "清官无辅", "checks": [check("official_clear", True, "官清无伤杀")],
                          "decisive": [], "damage": [], "rescues": {}, "unresolved_damage": [],
                          "grade": "无辅助成式", "outcome": "未成格", "xiang": []})

    elif chart.ge_ju in {"正财格", "偏财格"}:
        add("财旺生官", official, (wealth_root, control_root), {**hurting, **raw_k}, seal,
            damage_ten_gods=frozenset({"伤官"}) | groups["杀"])
        add("食伤生财", output, (strong, output_root), {**raw_p, **raw_k, **seal_attacks_output},
            {**official, **output}, transform_peers=True,
            damage_ten_gods=groups["比劫"] | groups["杀"] | groups["印"])
        add("财格配印", seal, (seal_root, check("wealth_seal_separated", not wealth_attacks_seal, "财印位置妥贴")),
            {**raw_p, **raw_k}, {**official, **output},
            damage_ten_gods=groups["比劫"] | groups["杀"])
        if raw_p:
            add("财逢劫而官制", official, (control_root,), {**raw_p, **hurting, **raw_k}, official, rescue=True,
                damage_ten_gods=groups["比劫"] | groups["杀"] | frozenset({"伤官"}))
        if raw_k:
            add("财逢杀而食制", output, (output_root,), {**raw_k, **seal_attacks_output}, output, rescue=True,
                damage_ten_gods=groups["杀"] | groups["印"])
        fail("wealth_light_peer_heavy", not features["财"]["strong"] and features["比劫"]["strong"] and bool(live["比劫"]),
             "财轻比重", live["比劫"])
        fail("wealth_feeds_killing", bool(live["杀"]), "财透七杀而未制合", live["杀"])

    elif chart.ge_ju == "食神格":
        owl = {ref: value for ref, value in raw_i.items() if chart.shi_shen[ref] == "偏印"}
        add("食神生财", wealth, (strong, wealth_root), {**owl, **raw_k}, wealth,
            damage_ten_gods=frozenset({"偏印"}) | groups["杀"])
        add("食神制杀", killing,
            (check("body_not_weak", not body_weak, "身有承受之根"), output_root),
            {**raw_w, **owl}, peers,
            damage_ten_gods=groups["财"] | frozenset({"偏印"}))
        add("弃食就杀印", seal,
            (check("killing_present", killing, "有杀印另取", killing), seal_root,
             check("body_weak", body_weak, "身轻用印化杀")),
            wealth_attacks_seal, peers,
            damage_ten_gods=groups["财"])
        fail("food_owl", bool({r: v for r, v in owl.items() if r not in combined}), "食神逢枭", owl)
        fail("food_wealth_killing", bool(wealth and killing), "食神生财而露杀", [*wealth, *killing])

    elif chart.ge_ju == "七杀格":
        month_killing = {ref: positions[ref] for ref in grid_refs if ref in positions}
        blade = {ref: value for ref, value in positions.items() if ref.startswith("bz.hidden.")
                 and chart.branches[ref.split(".")[2]] == REN_TABLE.get(chart.day_master)
                 and chart.shi_shen[ref] == "劫财"}
        add("食伤制杀", output,
            (check("body_not_weak", not body_weak, "身有承受之根"), output_root),
            {**raw_w, **seal_attacks_output, **raw_o}, peers,
            damage_ten_gods=groups["财"] | groups["印"] | groups["官"])
        add("杀印相生", seal, (seal_root, check("body_not_excess", not body_strong, "非身旺又增杀印")),
            wealth_attacks_seal, peers,
            damage_ten_gods=groups["财"])
        add("杀刃相济", blade,
            (check("blade_present", REN_TABLE.get(chart.day_master) in chart.branches.values(), "支有阳刃"),
             check("killing_rooted", any(rooted(ref) for ref in month_killing), "杀有根")),
            raw_o, output,
            damage_ten_gods=groups["官"])
        fail("killing_wealth_no_control", bool(wealth) and not (output or seal),
             "七杀逢财而无制化", wealth)

    combination_routes = {
        "正官格": ("合伤存官", hurting, ()),
        "正财格": ("合杀存财", raw_k, (wealth_root,)),
        "偏财格": ("合杀存财", raw_k, (wealth_root,)),
        "正印格": ("合财存印", raw_w, (seal_root,)),
        "偏印格": ("合财存印", raw_w, (seal_root,)),
    }
    if chart.ge_ju in combination_routes:
        name, targets, checks = combination_routes[chart.ge_ju]
        if targets:
            helpers = {combined[ref]: positions[combined[ref]] for ref in targets if ref in combined}
            add(name, helpers, checks, targets, helpers, rescue=True,
                damage_ten_gods=({"合伤存官": frozenset({"伤官"}), "合杀存财": groups["杀"],
                                 "合财存印": groups["财"]}[name]))

    assert paths, f"格局无候选判断链：{chart.ge_ju}"
    formed = [path for path in paths if path["outcome"] in {"成格", "败中有救"}]
    damaged = [path for path in paths if path["outcome"] == "成中有败"]
    matched_failures = [item for item in failures if item["matched"]]
    chosen = next(iter(formed or damaged), None)
    if chosen:
        status, variant = chosen["outcome"], chosen["name"]
        xiang_refs = chosen["xiang"]
        if chosen["unresolved_damage"]:
            # 未获救的作用不能反过来成为相神。
            xiang_refs = [ref for ref in xiang_refs if usable(ref)]
    else:
        status = "破格" if matched_failures else "未成格"
        variant = "／".join(item["name"] for item in matched_failures) or "常格成式未成立"
        xiang_refs = []
    # The main god is selected only inside this route, never by whole-chart weights.
    xiang = xiang_refs[0] if xiang_refs else None
    assert status not in {"成格", "败中有救"} or xiang, "成式必须有实际相神／辅用证据"
    basis = [
        "透干：" + "、".join(f"{key}{len(value)}处" for key, value in raw.items()),
        "根气：" + "、".join(f"{key}{value['roots']}支（本气{value['main_roots']}支）" for key, value in features.items()),
        *[f"{positions[a][0]}与{positions[b][0]}合绊：{a}↔{b}"
          for a, b in combined.items() if a < b],
        f"共检查{len(paths)}条取用途径；完整成立{len(formed)}条，带未救损伤{len(damaged)}条",
    ]
    if chosen:
        basis.append(f"采用{variant}（{chosen['grade']}）；成败为{status}")
        basis.extend(f"救应：{target}由{'、'.join(refs)}处理" for target, refs in chosen["rescues"].items())
        basis.extend(f"未救损伤：{ref}" for ref in chosen["unresolved_damage"])
    else:
        basis.extend(item["label"] for item in matched_failures)
        basis.extend(f"{path['name']}不成立：" + "；".join(c["label"] for c in path["checks"] if not c["passed"])
                     for path in paths if path["outcome"] == "rejected")
    chart.ge_ju_assessment = {
        "version": PATTERN_RULE_VERSION, "state": "not_formed" if status == "未成格" else "resolved",
        "method": "structural_paths_v2", "rule_id": f"{chart.ge_ju}.{variant}",
        "basis": basis, "conditions": [], "features": features, "paths": paths,
        "failure_checks": failures, "xiang_candidates": xiang_refs,
        "limitations": [
            "本结论是固定常格规则的结构判定，不是人生好坏或预测准确率",
            "根气强弱是公开的结构代理；合绊不当作化气，不穷尽从格、化气格与调候轻重",
            "未成格表示此版已列成式均未成立；不等于破格，也不等于软件待实现",
        ],
    }
    if chosen and xiang:
        favored = chart.shi_shen[xiang]
        chart.ge_ju_assessment["transit_preferences"] = {
            "favored_ten_gods": [favored],
            "avoided_ten_gods": sorted(transit_damage[chosen["name"]] - {favored}),
        }
    chart.ge_ju_variant = variant
    refs = _unique([*grid_refs, *xiang_refs])[:4]
    return status, xiang, [Evidence(
        system=System.BAZI, claim=f"{chart.ge_ju}以{variant}判为{status}（固定常格规则）",
        refs=refs, polarity=(Polarity.POSITIVE if status in {"成格", "败中有救"} else
                            Polarity.NEUTRAL if status == "未成格" else Polarity.NEGATIVE),
        weight=_evidence_weight(refs), source=source,
    )]


def _pattern_strength(chart: BaziChart, names: frozenset[str]) -> dict[str, object]:
    """保守、可复现的根气代理；不使用未披露的加权旺衰分数。"""
    elements = {STEM_PROPERTIES[stem][0] for stem in STEM_PROPERTIES
                if ten_god(chart.day_master, stem) in names}
    roots = {pillar for pillar, hidden in chart.hidden_stems.items()
             if any(stem and STEM_PROPERTIES[stem][0] in elements for stem in hidden.values())}
    main = {pillar for pillar, hidden in chart.hidden_stems.items()
            if hidden.get("benqi") and STEM_PROPERTIES[hidden["benqi"]][0] in elements}
    exposed = _exposed_locations_by_ten_god(chart, names)
    branches = set(chart.branches.values())
    assembly = any(required <= branches and element in elements
                   for required, element in (*THREE_COMBINATIONS, *THREE_MEETINGS))
    return {
        "roots": len(roots), "main_roots": len(main), "exposed": len(exposed),
        "root_refs": [ids.bz_hidden(pillar, layer) for pillar, hidden in chart.hidden_stems.items()
                      for layer, stem in hidden.items() if stem and STEM_PROPERTIES[stem][0] in elements],
        "assembly": assembly,
        "strong": assembly or len(main) >= 2 or ("month" in main and (len(roots) >= 2 or bool(exposed)))
        or (len(roots) >= 2 and len(exposed) >= 2),
    }






def _exposed_locations_by_ten_god(
    chart: BaziChart,
    names: frozenset[str],
) -> dict[str, tuple[str, float]]:
    """只取年月时透干；日主自身不作为子型条件。"""
    return {
        element_id: position
        for element_id, position in _all_stem_locations(chart).items()
        if (
            element_id in {ids.bz_stem("year"), ids.bz_stem("month"), ids.bz_stem("hour")}
            and chart.shi_shen[element_id] in names
        )
    }


def _all_stem_locations(chart: BaziChart) -> dict[str, tuple[str, float]]:
    """汇总四干与全部非空藏干，并标注位置权重。"""
    result: dict[str, tuple[str, float]] = {}
    for pillar in PILLAR_NAMES:
        result[ids.bz_stem(pillar)] = (chart.stems[pillar], constants.POSITION_WEIGHT["stem"])
        for layer in HIDDEN_STEM_LAYERS:
            stem = chart.hidden_stems[pillar][layer]
            if stem is not None:
                key = "month_hidden" if pillar == "month" else "hidden"
                result[ids.bz_hidden(pillar, layer)] = (stem, constants.POSITION_WEIGHT[key])
    return result


def _build_xiang_shen(chart: BaziChart, element_id: str | None) -> XiangShen | None:
    """一次性推导相神结构体，并断言 ID、天干、十神三者自洽。"""
    if element_id is None:
        return None
    positions = _all_stem_locations(chart)
    if element_id not in positions:
        raise AssertionError(f"相神不是有效天干位置：{element_id}")
    ids.validate_all([element_id])
    stem, _ = positions[element_id]
    expected = ten_god(chart.day_master, stem)
    actual = chart.shi_shen.get(element_id)
    if actual != expected:
        raise AssertionError(
            f"相神 {element_id} 的天干 {stem} 十神不一致：{actual!r} != {expected!r}"
        )
    return XiangShen(id=element_id, stem=stem, ten_god=actual)




def _build_ge_ju_yong_shen(chart: BaziChart) -> GeJuYongShen | None:
    """Only the adjudicated route may supply a principal auxiliary."""
    if chart.xiang_shen is None or chart.ge_ju_status is None:
        return None
    return GeJuYongShen(
        principle=f"{chart.ge_ju_variant}取{chart.xiang_shen.ten_god}",
        ten_gods=(chart.xiang_shen.ten_god,), primary=chart.xiang_shen,
    )


def _build_ge_ju_god(
    chart: BaziChart,
    grid: str,
    candidate_refs: list[str],
) -> GeJuGod:
    """从定格证据中固化格神；它不是成格用神或相神。"""
    target_ten_god = GRID_TEN_GOD.get(grid)
    if target_ten_god is None:
        raise AssertionError(f"格局没有对应格神十神：{grid}")
    positions = _all_stem_locations(chart)
    element_id = next(
        (
            ref for ref in candidate_refs
            if ref in positions and chart.shi_shen.get(ref) == target_ten_god
        ),
        None,
    )
    if element_id is None:
        raise AssertionError(f"{grid} 的决定性证据中找不到格神位置")
    ids.validate_all([element_id])
    stem, _ = positions[element_id]
    expected = ten_god(chart.day_master, stem)
    if expected != target_ten_god:
        raise AssertionError(
            f"格神 {element_id} 的天干 {stem} 与十神不一致："
            f"{expected!r} != {target_ten_god!r}"
        )
    return GeJuGod(id=element_id, stem=stem, ten_god=target_ten_god)




def _evidence_weight(refs: list[str]) -> float:
    """以证据中最强的实际盘面位置作为 Evidence 权重。"""
    if not refs:
        return 0.0
    return max(_position_weight(element_id) for element_id in refs)


def _position_weight(element_id: str) -> float:
    """从生成的 ID 反查透干、月令藏干或他支藏干的权重。"""
    for pillar in PILLAR_NAMES:
        if element_id == ids.bz_stem(pillar):
            return constants.POSITION_WEIGHT["stem"]
        for layer in HIDDEN_STEM_LAYERS:
            if element_id == ids.bz_hidden(pillar, layer):
                return constants.POSITION_WEIGHT["month_hidden"] if pillar == "month" else constants.POSITION_WEIGHT["hidden"]
    if element_id == ids.bz_siling():
        return constants.POSITION_WEIGHT["month_hidden"]
    return 0.0




def _unique(values: list[str]) -> list[str]:
    """保持顺序地去重位置 ID。"""
    return list(dict.fromkeys(values))
