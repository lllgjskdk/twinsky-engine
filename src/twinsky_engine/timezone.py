"""出生地坐标的离线 IANA 时区识别。"""

from __future__ import annotations

from datetime import datetime
from functools import lru_cache
from math import isfinite

import pytz
from timezonefinder import TimezoneFinder


@lru_cache(maxsize=1)
def _finder() -> TimezoneFinder:
    """复用只读时区边界索引，避免每个建档请求重复载入数据。"""
    return TimezoneFinder(in_memory=True)


def resolve_timezone(lat: float, lng: float) -> str:
    """由经纬度在本地推导 IANA 时区，不发送出生地数据到第三方。"""
    _validate_coordinate("lat", lat, -90.0, 90.0)
    _validate_coordinate("lng", lng, -180.0, 180.0)
    timezone = _finder().timezone_at(lng=lng, lat=lat)
    if timezone is None:
        raise ValueError("该坐标无法离线识别 IANA 时区，请手动填写并确认")
    return timezone


def timezone_offset_hours(local_time: datetime, timezone_name: str) -> float:
    """由 IANA 历史规则计算当地民用时偏移，并拒绝歧义或不存在的时刻。"""
    if local_time.tzinfo is not None:
        raise ValueError("当地民用时间不得附带 UTC 偏移")
    try:
        localized = pytz.timezone(timezone_name).localize(local_time, is_dst=None)
    except pytz.UnknownTimeZoneError as exc:
        raise ValueError(f"无效 IANA 时区：{timezone_name}") from exc
    except (pytz.AmbiguousTimeError, pytz.NonExistentTimeError) as exc:
        raise ValueError(f"出生时刻在 {timezone_name} 的夏令时规则中不唯一或不存在") from exc
    offset = localized.utcoffset()
    if offset is None:
        raise ValueError(f"无法计算 {timezone_name} 在出生时刻的 UTC 偏移")
    return offset.total_seconds() / 3600


def _validate_coordinate(name: str, value: float, lower: float, upper: float) -> None:
    """拒绝越界或非有限的坐标，避免把输入问题伪装成时区问题。"""
    if not isfinite(value) or not lower <= value <= upper:
        raise ValueError(f"{name} 须在 {lower} 至 {upper} 之间")
