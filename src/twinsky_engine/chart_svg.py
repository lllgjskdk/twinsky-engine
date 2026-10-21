"""双盘静态 SVG 渲染。所有可高亮位置均由 ``core.ids`` 生成 ID。"""

from __future__ import annotations

from datetime import date, datetime
from html import escape

from . import ids
from .schema import BaziChart, VedicChart

PILLARS = ("year", "month", "day", "hour")
HIDDEN_LAYERS = ("benqi", "zhongqi", "yuqi")
PILLAR_LABELS = {"year": "年柱", "month": "月柱", "day": "日柱", "hour": "时柱"}
LAYER_LABELS = {"benqi": "本", "zhongqi": "中", "yuqi": "余"}
FIVE_ELEMENT_COLORS = {
    "metal": "#E9C46A",
    "wood": "#66C487",
    "water": "#69A7FF",
    "fire": "#FF6B6B",
    "earth": "#C58A5A",
}
SYMBOL_ELEMENTS = {
    **dict.fromkeys("庚辛申酉", "metal"),
    **dict.fromkeys("甲乙寅卯", "wood"),
    **dict.fromkeys("壬癸亥子", "water"),
    **dict.fromkeys("丙丁巳午", "fire"),
    **dict.fromkeys("戊己辰戌丑未", "earth"),
}
RASI_POSITIONS = {
    "pisces": (0, 0), "aries": (1, 0), "taurus": (2, 0), "gemini": (3, 0),
    "cancer": (3, 1), "leo": (3, 2), "virgo": (3, 3), "libra": (2, 3),
    "scorpio": (1, 3), "sagittarius": (0, 3), "capricorn": (0, 2), "aquarius": (0, 1),
}
RASI_LABELS = {
    "aries": "Ar", "taurus": "Ta", "gemini": "Ge", "cancer": "Cn",
    "leo": "Le", "virgo": "Vi", "libra": "Li", "scorpio": "Sc",
    "sagittarius": "Sg", "capricorn": "Cp", "aquarius": "Aq", "pisces": "Pi",
}
RASI_NAMES_ZH = {
    "aries": "白羊座", "taurus": "金牛座", "gemini": "双子座", "cancer": "巨蟹座",
    "leo": "狮子座", "virgo": "处女座", "libra": "天秤座", "scorpio": "天蝎座",
    "sagittarius": "射手座", "capricorn": "摩羯座", "aquarius": "水瓶座", "pisces": "双鱼座",
}
GRAHA_NAMES_ZH = {
    "sun": "太阳", "moon": "月亮", "mars": "火星", "mercury": "水星",
    "jupiter": "木星", "venus": "金星", "saturn": "土星", "rahu": "罗喉", "ketu": "计都",
}
# Conventional two-letter graha marks keep four residents from colliding in one cell.
GRAHA_MARKS = {
    "sun": "Su", "moon": "Mo", "mars": "Ma", "mercury": "Me",
    "jupiter": "Ju", "venus": "Ve", "saturn": "Sa", "rahu": "Ra", "ketu": "Ke",
}
RASI_ORDER = tuple(RASI_LABELS)


def _i18n(text: str) -> str:
    """Tag a Chinese UI label so the page's i18n runtime swaps it for the chosen language."""
    return f' data-i18n="{escape(text)}"'


def _graha_mark(graha: str) -> str:
    return GRAHA_MARKS.get(graha, escape(graha[:2].title()))


def render_bazi_details(chart: BaziChart) -> str:
    """格局判断明细保留为隐藏内容，不占用盘面空间。"""
    assessment = chart.ge_ju_assessment
    if not assessment:
        return ""
    lines = [
        f"格局：{chart.ge_ju or '取格未定'}；路径：{chart.ge_ju_variant or '月令取格'}；"
        f"结构判断：{chart.ge_ju_status or '条件待复核'}",
        *(assessment.get("basis") or []),
        *(f"需复核：{item}" for item in assessment.get("conditions", [])),
    ]
    if chart.ge_ju_unavailable_reason and not assessment.get("conditions"):
        lines.append(chart.ge_ju_unavailable_reason)
    for path in assessment.get("paths", []):
        outcome = "条件不成立" if path["outcome"] == "rejected" else path["outcome"]
        lines.append(f"{path['name']}：{outcome}；" + "、".join(
            f"{'✓' if item['passed'] else '×'} {item['label']}" for item in path["checks"]))
    for alternative in assessment.get("alternatives", []):
        lines.append(f"仅作候选假设：若取{alternative['grid']}，该路径为{alternative['status']}；"
                     "未达到透会定格条件，不是已确认格局")
    lines.extend(assessment.get("limitations", []))
    lines.append(f"规则版本：{assessment.get('version', '未标记')}；旧报告不追改")
    return (
        '<details class="bazi-assessment" hidden><summary>格局判断依据</summary>'
        + "".join(f"<p>{escape(line)}</p>" for line in lines) + '</details>'
    )


def render_bazi_chart(chart: BaziChart, *, include_timing: bool = True) -> str:
    """渲染四柱；工作台已有交互时间轴，不再附带静态时间轴。"""
    columns: list[str] = []
    for index, pillar in enumerate(PILLARS):
        x = 20 + index * 126
        stem_id = ids.bz_stem(pillar)
        branch_id = ids.bz_branch(pillar)
        hidden = []
        for layer in HIDDEN_LAYERS:
            stem = chart.hidden_stems[pillar][layer]
            if stem is not None:
                hidden_id = ids.bz_hidden(pillar, layer)
                hidden.append(
                    f'<g id="{hidden_id}" class="chart-item hidden">'
                f'<text x="{x + 50}" y="{194 + len(hidden) * 18}" text-anchor="middle">'
                    f'{LAYER_LABELS[layer]}：{_colored_symbol(stem)}</text></g>'
                )
        columns.append(
            f'<g id="{ids.bz_pillar(pillar)}" class="chart-item pillar">'
            f'<rect x="{x}" y="32" width="100" height="208" rx="4"/>'
            f'<text x="{x + 50}" y="53" text-anchor="middle" class="pillar-label">{PILLAR_LABELS[pillar]}</text>'
            f'<g id="{stem_id}" class="chart-item">'
            f'<text x="{x + 50}" y="91" text-anchor="middle" class="stem">{_colored_symbol(chart.stems[pillar])}</text>'
            f'<text x="{x + 50}" y="111" text-anchor="middle" class="ten-god">'
            f'{escape(chart.shi_shen.get(stem_id, ""))}</text></g>'
            f'<g id="{branch_id}" class="chart-item">'
            f'<text x="{x + 50}" y="151" text-anchor="middle" class="branch">{_colored_symbol(chart.branches[pillar])}</text>'
            f'<text x="{x + 50}" y="174" text-anchor="middle" class="ten-god">地支</text></g>'
            f'{"".join(hidden)}</g>'
        )

    siling_id = ids.bz_siling()
    geju_id = ids.bz_geju()
    xiang = (
        "待裁决"
        if chart.xiang_shen_resolution_status.value in {"pending", "unresolved"}
        else "无"
    )
    if chart.xiang_shen is not None:
        xiang = f"{_colored_symbol(chart.xiang_shen.stem)}（{escape(chart.xiang_shen.ten_god)}）"
    geju_summary = _geju_summary(chart)
    geju_parts = geju_summary.split(" · ")
    geju_lines = [" · ".join(geju_parts[:2]), " · ".join(geju_parts[2:])]
    geju_lines = [line for line in geju_lines if line]
    timeline_offset = 34
    xiaoyun_items = []
    for index, cycle in enumerate(chart.xiao_yun if include_timing else ()):
        x = 18 + index * 50
        xiaoyun_items.append(
            '<g class="xiaoyun">'
            f'<rect x="{x}" y="{325 + timeline_offset}" width="44" height="42" rx="3"/>'
            f'<text x="{x + 22}" y="{343 + timeline_offset}" text-anchor="middle">{_colored_pillar(cycle.pillar)}</text>'
            f'<text x="{x + 22}" y="{358 + timeline_offset}" text-anchor="middle" class="tiny">{cycle.year}</text></g>'
        )

    dayun_y = (407 if xiaoyun_items else 325) + timeline_offset
    dayun_items = []
    for cycle in chart.da_yun if include_timing else ():
        x = 18 + (cycle.index - 1) * 50
        dayun_items.append(
            f'<g id="{cycle.id}" class="chart-item dayun">'
            f'<rect x="{x}" y="{dayun_y}" width="44" height="42" rx="3"/>'
            f'<text x="{x + 22}" y="{dayun_y + 18}" text-anchor="middle">{_colored_pillar(cycle.pillar)}</text>'
            f'<text x="{x + 22}" y="{dayun_y + 33}" text-anchor="middle" class="tiny">{cycle.start_year}</text></g>'
        )

    liunian_items = []
    liunian_columns = 10
    liunian_start_y = dayun_y + 85
    for index, cycle in enumerate(chart.liu_nian if include_timing else ()):
        column = index % liunian_columns
        row = index // liunian_columns
        x = 18 + column * 50
        y = liunian_start_y + row * 49
        liunian_items.append(
            f'<g id="{cycle.id}" class="chart-item liunian">'
            f'<rect x="{x}" y="{y}" width="44" height="41" rx="3"/>'
            f'<text x="{x + 22}" y="{y + 16}" text-anchor="middle">{_colored_pillar(cycle.pillar)}</text>'
            f'<text x="{x + 22}" y="{y + 32}" text-anchor="middle" class="tiny">{cycle.year}</text></g>'
        )
    liunian_rows = max(1, (len(chart.liu_nian) + liunian_columns - 1) // liunian_columns)
    chart_height = liunian_start_y + liunian_rows * 49 + 10 if include_timing else 335
    xiaoyun_label = (
        f'<text x="16" y="{315 + timeline_offset}" class="section-label">小运（交运前）</text>'
        if xiaoyun_items else ""
    )
    timing = (
        f'{xiaoyun_label}{"".join(xiaoyun_items)}'
        f'<text x="16" y="{dayun_y - 10}" class="section-label">大运</text>'
        f'{"".join(dayun_items)}'
        f'<text x="16" y="{liunian_start_y - 10}" class="section-label">流年（立春换年，出生至 120 岁）</text>'
        f'{"".join(liunian_items)}'
    ) if include_timing else ""
    return (
        f'<svg class="chart-svg bazi-svg" data-system="bazi" viewBox="0 0 530 {chart_height}" role="img" aria-label="八字盘">'
        f'<style>{_five_element_css()}</style>'
        '<text x="16" y="20" class="chart-title">八字盘</text>'
        f'{"".join(columns)}'
        f'<g id="{siling_id}" class="chart-item meta"><text x="16" y="268">月令司令：{_colored_symbol(chart.siling)}</text></g>'
        f'<text x="210" y="268" class="meta">日主：{_colored_symbol(chart.day_master)}</text>'
        f'<text x="340" y="268" class="meta">相神：{xiang}</text>'
        f'<g id="{geju_id}" class="chart-item meta" aria-label="{escape(geju_summary)}">'
        f'<text x="16" y="291">{escape(geju_lines[0])}</text>'
        f'{f"<text x=\"16\" y=\"311\">{escape(geju_lines[1])}</text>" if len(geju_lines) > 1 else ""}'
        '</g>'
        f'{timing}</svg>'
    )


def _colored_symbol(symbol: str) -> str:
    """为一个干支字附上统一的五行颜色类。"""
    element = SYMBOL_ELEMENTS.get(symbol)
    if element is None:
        raise ValueError(f"未知干支字：{symbol}")
    return f'<tspan class="element-{element}">{escape(symbol)}</tspan>'


def _colored_pillar(pillar: str) -> str:
    """分别着色一组干支，避免整柱被误用同一种颜色。"""
    return "".join(_colored_symbol(symbol) for symbol in pillar)


def _five_element_css() -> str:
    """生成集中可调的五行配色。"""
    return "".join(
        f".bazi-svg .element-{element}{{fill:{color}}}"
        for element, color in FIVE_ELEMENT_COLORS.items()
    )


def _geju_summary(chart: BaziChart) -> str:
    """展示已固化的格神；成败层未覆盖时公开降级。"""
    if chart.ge_ju is None:
        if chart.ge_ju_candidates:
            candidates = "／".join(item.grid for item in chart.ge_ju_candidates)
            return f"格局：{candidates}（候选待裁决）"
        reason = chart.ge_ju_unavailable_reason or "当前规则尚未完成定格"
        if reason.startswith(("比肩司令", "劫财司令")):
            return f"格局：{reason[:2]}司令（取格待核）"
        return f"格局：规则未覆盖（{reason}）"
    if chart.ge_ju_god is None:
        raise ValueError(f"{chart.ge_ju} 缺少已固化的格神")
    qualifiers = [
        item for item in (chart.ge_ju_clarity, chart.ge_ju_variant, chart.ge_ju_status)
        if item is not None
    ]
    if chart.ge_ju_status is None and chart.ge_ju_unavailable_reason:
        qualifiers.append("条件待复核" if chart.ge_ju_assessment.get("state") == "conditional" else "成败规则待补")
    grid_label = (
        f"{chart.ge_ju}（{'·'.join(qualifiers)}）"
        if qualifiers else chart.ge_ju
    )
    summary = (
        f"格局：{grid_label} · 格神："
        f"{chart.ge_ju_god.stem}（{chart.ge_ju_god.ten_god}）"
    )
    if chart.ge_ju_yong_shen is not None:
        yong = "、".join(chart.ge_ju_yong_shen.ten_gods)
        if chart.ge_ju_yong_shen.primary is not None:
            primary = chart.ge_ju_yong_shen.primary
            yong += f"·主用{primary.stem}（{primary.ten_god}）"
        summary += f" · 用神：{yong}"
    return summary


def render_vedic_chart(chart: VedicChart, *, as_of: date | None = None) -> str:
    """将南印度固定星座盘渲染为十二格 4×4 外环，中央 2×2 留空。"""
    houses_by_rasi = {data["rasi"]: (number, data) for number, data in chart.houses.items()}
    cells: list[str] = []
    cell_size = 96
    for rasi, (column, row) in RASI_POSITIONS.items():
        number, house = houses_by_rasi[rasi]
        x = column * cell_size
        y = row * cell_size
        planet_items = []
        planet_index = 0
        for graha, data in chart.grahas.items():
            if data["rasi"] == rasi:
                planet_items.append(
                    f'<g id="{ids.vd_graha(graha)}" class="chart-item graha">'
                    f'<text x="{x + 8 + (planet_index % 3) * 30}" y="{y + 55 + (planet_index // 3) * 16}">'
                    f'{_graha_mark(graha)}</text></g>'
                )
                planet_index += 1
        lagna = ""
        if rasi == chart.lagna_rasi:
            lagna = (
                f'<g id="{ids.vd_lagna()}" class="chart-item lagna">'
                f'<text x="{x + 74}" y="{y + 21}" text-anchor="middle">Lg</text></g>'
            )
        cells.append(
            f'<g id="{ids.vd_house(number)}" class="chart-item house" data-rasi="{rasi}">'
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}"/>'
            f'<g id="{ids.vd_rasi(rasi)}" class="chart-item rasi">'
            f'<text x="{x + 8}" y="{y + 20}">{RASI_LABELS[rasi]}</text></g>'
            f'<text x="{x + 88}" y="{y + 88}" text-anchor="end" class="house-number">{number}</text>'
            f'{lagna}{"".join(planet_items)}</g>'
        )
    dasha_items = _active_dasha_items(chart, as_of or date.today())
    dasha_height = 528
    profile_rows = (
        ("上升", chart.lagna_rasi),
        ("月亮", str(chart.grahas["moon"]["rasi"])),
        ("太阳", str(chart.grahas["sun"]["rasi"])),
    )
    profile = "".join(
        f'<text x="{64 + index * 128}" y="405" text-anchor="middle" class="tiny"{_i18n(label)}>{escape(label)}</text>'
        f'<text x="{64 + index * 128}" y="426" text-anchor="middle" class="rasi"{_i18n(RASI_NAMES_ZH[rasi])}>{RASI_NAMES_ZH[rasi]}</text>'
        for index, (label, rasi) in enumerate(profile_rows)
    )
    return (
        f'<svg class="chart-svg vedic-svg" data-system="vedic" viewBox="0 0 384 {dasha_height}" role="img" aria-label="南印度式印占盘" data-i18n-aria-label="南印度式印占盘">'
        f'{"".join(cells)}'
        f'<g class="d1-profile">{profile}</g>'
        f'{"".join(dasha_items)}</svg>'
    )


def render_varga_chart(chart: VedicChart, division: str) -> str:
    """渲染任一已开放分盘，并为上升、宫位、星座和九曜绑定独立 ID。"""
    if division not in ids.VARGAS or division == "d1":
        raise ValueError(f"暂不支持的分盘：{division}")
    varga = chart.vargas.get(division)
    if varga is None:
        return ""
    lagna_rasi = str(varga["lagna"]["rasi"])
    lagna_index = RASI_ORDER.index(lagna_rasi)
    cells: list[str] = []
    cell_size = 96
    for rasi, (column, row) in RASI_POSITIONS.items():
        house = (RASI_ORDER.index(rasi) - lagna_index) % len(RASI_ORDER) + 1
        x = column * cell_size
        y = row * cell_size
        resident_grahas = [
            graha for graha, data in varga["grahas"].items()
            if data["rasi"] == rasi
        ]
        planet_items = []
        for planet_index, graha in enumerate(resident_grahas):
            planet_items.append(
                f'<g id="{ids.vd_graha(graha, division)}" class="chart-item graha">'
                f'<text x="{x + 8 + (planet_index % 3) * 30}" '
                f'y="{y + 55 + (planet_index // 3) * 16}">'
                f'{_graha_mark(graha)}</text></g>'
            )
        lagna = ""
        if rasi == lagna_rasi:
            lagna = (
                f'<g id="{ids.vd_lagna(division)}" class="chart-item lagna">'
                f'<text x="{x + 74}" y="{y + 21}" text-anchor="middle">Lg</text></g>'
            )
        cells.append(
            f'<g id="{ids.vd_house(house, division)}" class="chart-item house" data-rasi="{rasi}">'
            f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}"/>'
            f'<g id="{ids.vd_rasi(rasi, division)}" class="chart-item rasi">'
            f'<text x="{x + 8}" y="{y + 20}">{RASI_LABELS[rasi]}</text></g>'
            f'<text x="{x + 88}" y="{y + 88}" text-anchor="end" class="house-number">{house}</text>'
            f'{lagna}{"".join(planet_items)}</g>'
        )
    return (
        f'<svg class="chart-svg varga-svg" data-system="vedic" viewBox="0 0 384 384" role="img" aria-label="{division.upper()} 吠陀分盘">'
        f'<text x="6" y="-8" class="chart-title" data-i18n="{{division}} 分盘" '
        f'data-i18n-values=\'{{"division": "{division.upper()}"}}\'>{division.upper()} 分盘</text>{"".join(cells)}</svg>'
    )


def _active_dasha_items(chart: VedicChart, as_of: date) -> list[str]:
    """显示当前生效的大运层级，使时间类 Evidence 也能定位到右侧盘面。"""
    active: list[dict[str, object]] = []
    moment = datetime.combine(as_of, datetime.min.time())
    periods = chart.dashas
    while periods:
        current = next(
            (
                period for period in periods
                if period["start"] <= moment < period["end"]
            ),
            None,
        )
        if current is None:
            break
        active.append(current)
        periods = current.get("subperiods", [])  # type: ignore[assignment]
    labels = ("当前大运", "当前二级运")
    lords = [GRAHA_NAMES_ZH.get(str(entry["lord"]), str(entry["lord"])) for entry in active[:2]]
    return [
        (
            f'<g id="{entry["id"]}" class="chart-item dasha d1-dasha">'
            f'<rect x="{8 + index * 188}" y="442" width="180" height="78" rx="10"/>'
            f'<text x="{20 + index * 188}" y="460" class="tiny"{_i18n(labels[index])}>{labels[index]}</text>'
            f'<text x="{20 + index * 188}" y="481" class="rasi"{_i18n(lord)}>{escape(lord)}</text>'
            # Dates get their own line: "Mercury" or "ケートゥ" beside them would overlap.
            f'<text x="{20 + index * 188}" y="502" class="tiny">'
            f'{entry["start"].strftime("%Y.%m")}—{entry["end"].strftime("%Y.%m")}</text></g>'
        )
        for index, (entry, lord) in enumerate(zip(active[:2], lords))
    ]
