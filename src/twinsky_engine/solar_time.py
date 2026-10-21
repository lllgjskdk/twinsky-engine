"""标准时、经度校正时间与含均时差的真太阳时计算。"""

from __future__ import annotations

from datetime import datetime, timedelta
from math import cos, isfinite, pi, sin

from .schema import BirthInput

MINUTES_PER_DEGREE = 4.0


def longitude_correction_minutes(lng: float, tz_offset: float) -> float:
    """计算出生地相对时区标准经线的经度时差（单位：分钟）。"""
    _validate_finite("lng", lng)
    _validate_finite("tz_offset", tz_offset)
    timezone_meridian = tz_offset * 15.0
    return (lng - timezone_meridian) * MINUTES_PER_DEGREE


def equation_of_time_minutes(utc_datetime: datetime) -> float:
    """以 NOAA 的太阳位置级数计算均时差，返回视太阳时减平太阳时的分钟数。

    公式仅依赖日期与时刻，不调用外部服务；全年误差量级适用于八字时柱的
    分钟级校正。输入应为同一出生瞬间的 UTC 时刻。
    """
    day_of_year = utc_datetime.timetuple().tm_yday
    seconds = (
        utc_datetime.hour * 3600
        + utc_datetime.minute * 60
        + utc_datetime.second
        + utc_datetime.microsecond / 1_000_000
    )
    fractional_year = 2.0 * pi / 365.0 * (day_of_year - 1 + (seconds / 3600.0 - 12.0) / 24.0)

    return 229.18 * (
        0.000075
        + 0.001868 * cos(fractional_year)
        - 0.032077 * sin(fractional_year)
        - 0.014615 * cos(2.0 * fractional_year)
        - 0.040849 * sin(2.0 * fractional_year)
    )


def populate_solar_times(birth: BirthInput) -> BirthInput:
    """计算并填充 ``BirthInput`` 的三种时间，返回同一实例。

    ``raw_datetime`` 视为出生地的民用标准时；经度时差按 the TwinSky project spec §4.3
    直接以出生经度减时区标准经线计算。均时差则在该民用时刻对应的 UTC
    瞬间计算，符号为“视太阳时 - 平太阳时”。
    """
    correction = longitude_correction_minutes(birth.lng, birth.tz_offset)
    utc_datetime = birth.raw_datetime - timedelta(hours=birth.tz_offset)
    eot = equation_of_time_minutes(utc_datetime)

    birth.t_standard = birth.raw_datetime
    birth.t_longitude = birth.raw_datetime + timedelta(minutes=correction)
    birth.t_longitude_eot = birth.t_longitude + timedelta(minutes=eot)
    return birth


def _validate_finite(name: str, value: float) -> None:
    """拒绝无穷与 NaN，避免把无效坐标静默写入盘数据。"""
    if not isfinite(value):
        raise ValueError(f"{name} 须为有限数值，收到 {value!r}")
