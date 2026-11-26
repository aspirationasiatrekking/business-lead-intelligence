import csv

import pytest
from openpyxl import load_workbook

from src.lead_intelligence.exporters.atomic_output import atomic_output
from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
    sanitize_csv_value,
)
from src.lead_intelligence.exporters.excel_exporter import export_businesses_to_excel
from src.lead_intelligence.models.business import Business


@pytest.fixture(
    params=[
        (export_businesses_to_csv, ".csv"),
        (export_businesses_to_excel, ".xlsx"),
    ]
)
def destination(request, tmp_path):
    exporter, extension = request.param
    return exporter, tmp_path / f"leads{extension}"


def test_no_overwrite_and_explicit_replacement(destination):
    exporter, path = destination
    exporter([Business(name="Original")], path)
    original = path.read_bytes()
    with pytest.raises(FileExistsError):
        exporter([Business(name="Replacement")], path)
    assert path.read_bytes() == original
    exporter([Business(name="Replacement")], path, overwrite=True)
    assert path.read_bytes() != original
    assert list(path.parent.iterdir()) == [path]


@pytest.mark.parametrize("invalid", ["a\x00b", "a\x0bb", "a\ud800b", "a\ufffeb"])
def test_invalid_text_keeps_previous_file(destination, invalid):
    exporter, path = destination
    exporter([Business(name="Original")], path)
    original = path.read_bytes()
    with pytest.raises(ValueError, match="invalid XML"):
        exporter([Business(name=invalid)], path, overwrite=True)
    assert path.read_bytes() == original
    assert list(path.parent.iterdir()) == [path]


def test_invalid_text_does_not_publish_new_file(destination):
    exporter, path = destination
    with pytest.raises(ValueError):
        exporter([Business(name="Valid"), Business(name="a\x00b")], path)
    assert not path.exists()
    assert list(path.parent.iterdir()) == []


def test_invalid_extension_and_missing_parent(destination):
    exporter, path = destination
    with pytest.raises(ValueError, match="filename"):
        exporter([], path.with_suffix(".txt"))
    with pytest.raises(FileNotFoundError, match="parent"):
        exporter([], path.parent / "missing" / path.name)
    assert list(path.parent.iterdir()) == []


def test_atomic_writer_cleans_up_after_failure(tmp_path):
    target = tmp_path / "leads.csv"
    with pytest.raises(OSError, match="simulated"):
        with atomic_output(target, ".csv") as temporary:
            temporary.write_text("partial", encoding="utf-8")
            raise OSError("simulated failure")
    assert list(tmp_path.iterdir()) == []


def test_atomic_writer_does_not_clobber_concurrent_destination(tmp_path):
    target = tmp_path / "leads.csv"
    with pytest.raises(FileExistsError):
        with atomic_output(target, ".csv") as temporary:
            temporary.write_text("new", encoding="utf-8")
            target.write_text("other writer", encoding="utf-8")
    assert target.read_text(encoding="utf-8") == "other writer"
    assert list(tmp_path.iterdir()) == [target]


@pytest.mark.parametrize(
    "value", ["\ufeff=1+1", "\u200b@SUM(A1)", " \ttext", "\u2060＋1", "﹦1+1"]
)
def test_csv_detects_hidden_and_compatibility_prefixes(value):
    assert sanitize_csv_value(value) == "'" + value


@pytest.mark.parametrize("value", ["A" * 32768, "😀" * 16384])
def test_excel_rejects_oversized_cells_without_truncation(tmp_path, value):
    target = tmp_path / "leads.xlsx"
    with pytest.raises(ValueError, match="32767"):
        export_businesses_to_excel([Business(name="Agency", address=value)], target)
    assert list(tmp_path.iterdir()) == []


def test_excel_cell_boundary_and_error_literal(tmp_path):
    target = tmp_path / "leads.xlsx"
    address = "A" * 32767
    export_businesses_to_excel([Business(name="#N/A", address=address)], target)
    workbook = load_workbook(target)
    try:
        assert workbook.active["A2"].value == "#N/A"
        assert workbook.active["A2"].data_type == "s"
        assert workbook.active["B2"].value == address
    finally:
        workbook.close()


def test_csv_preserves_long_text(tmp_path):
    target = tmp_path / "leads.csv"
    address = "नेपाल 😀 " * 5000
    export_businesses_to_csv([Business(name="Agency", address=address)], target)
    with target.open(encoding="utf-8-sig", newline="") as stream:
        assert list(csv.reader(stream))[1][1] == address.strip()
