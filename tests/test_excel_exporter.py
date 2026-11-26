import pytest
from openpyxl import load_workbook

from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.models.business import Business

EXPECTED_HEADERS = [
    "Business Name",
    "Address",
    "Emails",
    "Phone Numbers",
    "Website",
    "Category",
    "City",
    "District",
    "State",
    "Country",
    "Country Code",
    "Source URLs",
    "Contact Page URLs",
    "Extraction Status",
    "Lead Score",
    "Lead Quality",
]


def test_export_businesses_to_excel(tmp_path):
    businesses = [
        Business(
            name="Nepal Hiking Team",
            address="Thamel, Kathmandu",
            emails=["info@nepalhikingteam.com"],
            phone_numbers=["01-4989212"],
            website="https://nepalhikingteam.com",
            category="Travel agency",
        ),
        Business(
            name="Nepal Trekking Experts",
            address="Kathmandu",
            emails=[
                "info@nepaltrekkingexperts.com",
                "sales@nepaltrekkingexperts.com",
            ],
            phone_numbers=["984-1917136"],
            website="https://nepaltrekkingexperts.com",
            category="Tour agency",
        ),
    ]

    output_file = tmp_path / "business_leads.xlsx"

    export_businesses_to_excel(
        businesses,
        str(output_file),
        region="NP",
    )

    assert output_file.exists()

    workbook = load_workbook(output_file)

    try:
        worksheet = workbook.active

        assert worksheet.title == "Business Leads"
        assert worksheet.max_row == 3
        assert worksheet.max_column == 16

        assert [cell.value for cell in worksheet[1]] == EXPECTED_HEADERS

        assert worksheet["A2"].value == "Nepal Hiking Team"
        assert worksheet["C2"].value == "info@nepalhikingteam.com"
        assert worksheet["D2"].value == "01-4989212"

        assert worksheet["C3"].value == (
            "info@nepaltrekkingexperts.com; sales@nepaltrekkingexperts.com"
        )

        assert worksheet["O2"].value == 100
        assert worksheet["P2"].value == "High"

        assert worksheet["O3"].value == 100
        assert worksheet["P3"].value == "High"

        assert worksheet["N2"].value == "pending"

        assert worksheet.freeze_panes == "A2"
        assert worksheet.auto_filter.ref == "A1:P3"

    finally:
        workbook.close()


def test_export_empty_business_list(tmp_path):
    output_file = tmp_path / "empty_leads.xlsx"

    export_businesses_to_excel(
        [],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        worksheet = workbook.active

        assert worksheet.max_row == 1
        assert worksheet.max_column == 16

        assert [cell.value for cell in worksheet[1]] == EXPECTED_HEADERS

    finally:
        workbook.close()


def test_export_business_without_emails(tmp_path):
    business = Business(name="Example Adventures")

    output_file = tmp_path / "no_emails.xlsx"

    export_businesses_to_excel(
        [business],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        worksheet = workbook.active

        assert worksheet["C2"].value is None
        assert worksheet["O2"].value == 0
        assert worksheet["P2"].value == "Low"

    finally:
        workbook.close()


@pytest.mark.parametrize(
    "malicious_value",
    [
        "=1+1",
        "+1+1",
        "-1+1",
        "@SUM(A1:A2)",
        "  =1+1",
        "\t=1+1",
    ],
)
def test_export_formula_like_business_names_as_text(
    tmp_path,
    malicious_value,
):
    business = Business(name=malicious_value)

    output_file = tmp_path / "formula_injection.xlsx"

    export_businesses_to_excel(
        [business],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        cell = workbook.active["A2"]

        assert cell.value == malicious_value.strip()
        assert cell.data_type == "s"

    finally:
        workbook.close()


@pytest.mark.parametrize(
    "malicious_value",
    [
        "  =1+1",
        "\t=1+1",
        "\n=1+1",
    ],
)
def test_excel_export_handles_unnormalized_formula_values(
    tmp_path,
    malicious_value,
):
    business = Business(name="Example Business")

    business.name = malicious_value

    output_file = tmp_path / "unsafe_value.xlsx"

    export_businesses_to_excel(
        [business],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        cell = workbook.active["A2"]

        assert cell.value == malicious_value
        assert cell.data_type == "s"

    finally:
        workbook.close()


def test_excel_exports_phone_numbers_as_text(tmp_path):
    business = Business(
        name="Example Business",
        phone_numbers=["+9779846041887"],
    )

    output_file = tmp_path / "phone.xlsx"

    export_businesses_to_excel(
        [business],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        cell = workbook.active["D2"]

        assert cell.value == "+9779846041887"
        assert cell.data_type == "s"

    finally:
        workbook.close()


def test_excel_exports_scores_as_numeric_values(tmp_path):
    business = Business(
        name="Example Business",
        lead_score=85,
    )

    output_file = tmp_path / "scores.xlsx"

    export_businesses_to_excel(
        [business],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        cell = workbook.active["O2"]

        assert cell.value == 85
        assert cell.data_type == "n"

    finally:
        workbook.close()


def test_excel_header_formatting(tmp_path):
    output_file = tmp_path / "formatting.xlsx"

    export_businesses_to_excel(
        [Business(name="Example Business")],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        worksheet = workbook.active
        cell = worksheet["A1"]

        assert cell.font.bold is True
        assert cell.fill.fill_type == "solid"
        assert cell.alignment.horizontal == "center"
        assert worksheet.row_dimensions[1].height == 30

    finally:
        workbook.close()


def test_excel_column_widths_are_bounded(tmp_path):
    business = Business(
        name="Example Business",
        address="A" * 1000,
    )

    output_file = tmp_path / "widths.xlsx"

    export_businesses_to_excel(
        [business],
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        worksheet = workbook.active

        for dimension in worksheet.column_dimensions.values():
            assert 12 <= dimension.width <= 50

        assert worksheet.column_dimensions["B"].width == 50

    finally:
        workbook.close()


def test_excel_quality_formatting(tmp_path):
    businesses = [
        Business(name="High Lead", lead_score=90),
        Business(name="Medium Lead", lead_score=60),
        Business(name="Low Lead", lead_score=20),
    ]

    output_file = tmp_path / "quality.xlsx"

    export_businesses_to_excel(
        businesses,
        str(output_file),
    )

    workbook = load_workbook(output_file)

    try:
        worksheet = workbook.active

        assert worksheet["P2"].value == "High"
        assert worksheet["P3"].value == "Medium"
        assert worksheet["P4"].value == "Low"

        assert worksheet["P2"].font.color.rgb.endswith("166534")
        assert worksheet["P3"].font.color.rgb.endswith("92400E")
        assert worksheet["P4"].font.color.rgb.endswith("64748B")

    finally:
        workbook.close()
