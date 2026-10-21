"""Single Jyotish fact-eligibility policy; legacy storage values remain readable."""

from enum import Enum


class BirthPrecision(str, Enum):
    DATE = "DATE"
    TIME_RANGE = "TIME_RANGE"
    MINUTE = "MINUTE"
    SECOND = "SECOND"


def birth_precision(birth):
    value = str(getattr(birth.precision, "value", birth.precision))
    if value in {"unknown", "DATE"}:
        return BirthPrecision.DATE
    if value in {"period", "TIME_RANGE"}:
        return BirthPrecision.TIME_RANGE
    if value == "SECOND" or (value == "exact" and (birth.raw_datetime.second or birth.raw_datetime.microsecond)):
        return BirthPrecision.SECOND
    if value in {"exact", "MINUTE"}:
        return BirthPrecision.MINUTE
    raise ValueError(f"Unknown birth precision: {value}")


def allows_fact(precision, fact_kind, *, stable_over_range=False):
    precision = BirthPrecision(precision)
    if precision in {BirthPrecision.MINUTE, BirthPrecision.SECOND}:
        return True
    # A sign may be usable at coarse precision ONLY with interval stability proof.
    # Existing period input has no bounds: do not pretend a sampled instant is proof.
    return fact_kind == "planet_sign" and stable_over_range
