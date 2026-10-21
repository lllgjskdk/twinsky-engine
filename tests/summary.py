"""Digest of a BaZi chart, shared by the golden test here and tools/export_engine.py in the TwinSky app.

Floats are rounded to 6 decimals and 8 equals 8.0, so last-bit differences between platforms do not
count as a change; set order is fixed, since it changes with each process's hash seed.
"""

from __future__ import annotations

import hashlib
import json


def _canonical(value):
    if isinstance(value, dict):
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_canonical(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_canonical(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True, default=str))
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 6)
    return value


def digest(value) -> str:
    text = json.dumps(_canonical(value), ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
