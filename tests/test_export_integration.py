import csv
from unittest.mock import Mock

import pytest
from openpyxl import load_workbook

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
)
from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.exporters.export_schema import (
    EXPORT_HEADERS,
    serialize_business,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import (
    ExtractionStatus,
)
from src.lead_intelligence.services.lead_scoring import (
    LeadScoringService,
)


@pytest.fixture
def complete_business():
    return Business(
        name="Example Trekking",
        address="Thamel, Kathmandu, Nepal",
        emails=[
            "info@example.com",
            "sales@example.com",
        ],
        phone_numbers=[
            "+9779846041887",
            "+97714989212",
        ],
        website="https://example.com",
        category="Travel agency",
        city="Kathmandu",
        district="Kathmandu",
        state="Bagmati",
        country="Nepal",
        country_code="NP",
        source_urls=[
            "https://example.com",
            "https://example.com/contact",
        ],
        contact_page_urls=[
            "https://example.com/contact",
            "https://example.com/about",
        ],
        extraction_status=ExtractionStatus.SUCCESS,
        lead_score=100,
    )


def read_csv(path):
    with open(
        path,
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.reader(file))


def read_excel(path):
    workbook = load_workbook(path)

    try:
        worksheet = workbook.active

        return list(worksheet.iter_rows(values_only=True))

    finally:
        workbook.close()


def test_shared_export_schema_contains_all_fields():
    assert len(EXPORT_HEADERS) == 16

    assert len(set(EXPORT_HEADERS)) == 16


def test_serialize_complete_business(complete_business):
    service = LeadScoringService()

    values = serialize_business(
        complete_business,
        scoring_service=service,
    )

    assert values == [
        "Example Trekking",
        "Thamel, Kathmandu, Nepal",
        "info@example.com; sales@example.com",
        "+9779846041887, +97714989212",
        "https://example.com",
        "Travel agency",
        "Kathmandu",
        "Kathmandu",
        "Bagmati",
        "Nepal",
        "NP",
        "https://example.com; https://example.com/contact",
        ("https://example.com/contact; https://example.com/about"),
        "success",
        100,
        "High",
    ]


@pytest.mark.parametrize(
    ("score", "quality"),
    [
        (0, "Low"),
        (49, "Low"),
        (50, "Medium"),
        (79, "Medium"),
        (80, "High"),
        (100, "High"),
    ],
)
def test_serializer_uses_stored_score(
    score,
    quality,
):
    business = Business(
        name="Example Business",
        lead_score=score,
    )

    service = Mock(spec=LeadScoringService)

    values = serialize_business(
        business,
        scoring_service=service,
    )

    assert values[14] == score
    assert values[15] == quality

    service.score_business.assert_not_called()


def test_serializer_calculates_missing_score():
    business = Business(
        name="Example Business",
        emails=["info@example.com"],
    )

    service = LeadScoringService()

    values = serialize_business(
        business,
        scoring_service=service,
    )

    assert values[14] == 30
    assert values[15] == "Low"

    # Serialization must not modify the business.
    assert business.lead_score is None


def test_serializer_passes_region_for_missing_score():
    business = Business(
        name="Example Business",
    )

    service = Mock(spec=LeadScoringService)

    service.score_business.return_value = 20

    values = serialize_business(
        business,
        scoring_service=service,
        region="NP",
    )

    service.score_business.assert_called_once_with(
        business,
        region="NP",
    )

    assert values[14] == 20


@pytest.mark.parametrize(
    "status",
    list(ExtractionStatus),
)
def test_serializer_exports_all_extraction_statuses(
    status,
):
    business = Business(
        name="Example Business",
        extraction_status=status,
    )

    values = serialize_business(
        business,
        scoring_service=LeadScoringService(),
    )

    assert values[13] == status.value


def test_serializer_preserves_unknown_geography():
    business = Business(name="Example Business")

    values = serialize_business(
        business,
        scoring_service=LeadScoringService(),
    )

    assert values[6:11] == [
        None,
        None,
        None,
        None,
        None,
    ]


def test_excel_and_csv_headers_are_identical(
    tmp_path,
    complete_business,
):
    csv_path = tmp_path / "leads.csv"
    excel_path = tmp_path / "leads.xlsx"

    export_businesses_to_csv(
        [complete_business],
        str(csv_path),
    )

    export_businesses_to_excel(
        [complete_business],
        str(excel_path),
    )

    csv_rows = read_csv(csv_path)
    excel_rows = read_excel(excel_path)

    assert csv_rows[0] == list(excel_rows[0])
    assert csv_rows[0] == list(EXPORT_HEADERS)


def test_excel_and_csv_export_consistent_business_data(
    tmp_path,
    complete_business,
):
    csv_path = tmp_path / "leads.csv"
    excel_path = tmp_path / "leads.xlsx"

    export_businesses_to_csv(
        [complete_business],
        str(csv_path),
    )

    export_businesses_to_excel(
        [complete_business],
        str(excel_path),
    )

    csv_values = read_csv(csv_path)[1]
    excel_values = read_excel(excel_path)[1]

    assert len(csv_values) == 16
    assert len(excel_values) == 16

    for index, excel_value in enumerate(excel_values):
        if index == 3:
            # CSV phone numbers have formula protection.
            assert csv_values[index] == f"'{excel_value}"

        else:
            assert csv_values[index] == str(excel_value)


def test_exporters_handle_missing_optional_fields(
    tmp_path,
):
    business = Business(
        name="Example Business",
    )

    csv_path = tmp_path / "empty_fields.csv"
    excel_path = tmp_path / "empty_fields.xlsx"

    export_businesses_to_csv(
        [business],
        str(csv_path),
    )

    export_businesses_to_excel(
        [business],
        str(excel_path),
    )

    csv_values = read_csv(csv_path)[1]
    excel_values = read_excel(excel_path)[1]

    for index in range(1, 13):
        assert csv_values[index] == ""
        assert excel_values[index] is None

    assert csv_values[13] == "pending"
    assert excel_values[13] == "pending"

    assert csv_values[14] == "0"
    assert excel_values[14] == 0

    assert csv_values[15] == "Low"
    assert excel_values[15] == "Low"


def test_formula_protection_covers_new_export_fields(
    tmp_path,
):
    business = Business(
        name="Example Business",
        city="=1+1",
        district="+1+1",
        state="-1+1",
        country="@SUM(A1:A2)",
        source_urls=["=1+1"],
        contact_page_urls=["+1+1"],
    )

    csv_path = tmp_path / "protected.csv"
    excel_path = tmp_path / "protected.xlsx"

    export_businesses_to_csv(
        [business],
        str(csv_path),
    )

    export_businesses_to_excel(
        [business],
        str(excel_path),
    )

    csv_values = read_csv(csv_path)[1]

    workbook = load_workbook(excel_path)

    try:
        worksheet = workbook.active

        expected = {
            6: "=1+1",
            7: "+1+1",
            8: "-1+1",
            9: "@SUM(A1:A2)",
            11: "=1+1",
            12: "+1+1",
        }

        for index, value in expected.items():
            assert csv_values[index] == f"'{value}"

            cell = worksheet.cell(
                row=2,
                column=index + 1,
            )

            assert cell.value == value
            assert cell.data_type == "s"

    finally:
        workbook.close()


def test_exporters_do_not_modify_businesses(
    tmp_path,
    complete_business,
):
    original_emails = complete_business.emails.copy()
    original_phones = complete_business.phone_numbers.copy()
    original_sources = complete_business.source_urls.copy()

    complete_business.lead_score = None

    export_businesses_to_csv(
        [complete_business],
        str(tmp_path / "leads.csv"),
    )

    export_businesses_to_excel(
        [complete_business],
        str(tmp_path / "leads.xlsx"),
    )

    assert complete_business.emails == original_emails
    assert complete_business.phone_numbers == original_phones
    assert complete_business.source_urls == original_sources
    assert complete_business.lead_score is None


def test_serializer_rejects_invalid_stored_score():
    business = Business(
        name="Example Business",
    )

    # Simulate an invalid mutation after construction.
    business.lead_score = 101

    with pytest.raises(ValueError):
        serialize_business(
            business,
            scoring_service=LeadScoringService(),
        )


@pytest.mark.parametrize(
    ("exporter", "extension"),
    [
        (export_businesses_to_csv, "csv"),
        (export_businesses_to_excel, "xlsx"),
    ],
)
def test_export_preserves_stored_zero_score(
    tmp_path,
    exporter,
    extension,
):
    business = Business(
        name="Example Business",
        emails=["info@example.com"],
        lead_score=0,
    )

    output_file = tmp_path / f"zero.{extension}"

    exporter(
        [business],
        str(output_file),
    )

    if extension == "csv":
        values = read_csv(output_file)[1]

        assert values[14] == "0"

    else:
        values = read_excel(output_file)[1]

        assert values[14] == 0

    assert values[15] == "Low"
