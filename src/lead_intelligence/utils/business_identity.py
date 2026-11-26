import math


def normalize_serper_cid(value: object) -> str | None:
    """Accept positive decimal identifiers within the unsigned 64-bit range."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or len(value) > 20 or not value.isascii() or not value.isdecimal():
        return None
    number = int(value)
    return str(number) if 0 < number <= 2**64 - 1 else None


def normalize_coordinate(value: object, limit: int) -> float | None:
    """Reject nonnumeric, nonfinite and out-of-range coordinates."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not -limit <= value <= limit or not math.isfinite(value):
        return None
    return float(value)
