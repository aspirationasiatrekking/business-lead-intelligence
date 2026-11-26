"""Reject unsafe or unrepresentable export text without losing data."""

import re

# XML 1.0 disallows these characters; also reject them in CSV for consistency.
INVALID_TEXT = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]")
MAX_EXCEL_CELL_UNITS = 32_767
MAX_EXCEL_ROWS = 1_048_576


def validate_export_text(value: object, *, excel: bool = False) -> None:
    if not isinstance(value, str):
        return
    if INVALID_TEXT.search(value):
        raise ValueError("Export text contains an invalid XML character.")
    if excel and len(value.encode("utf-16-le")) // 2 > MAX_EXCEL_CELL_UNITS:
        raise ValueError("Excel cell exceeds the 32767 UTF-16 unit limit.")
