import pytest
from openpyxl import load_workbook

from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.models.business import Business


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

    export_businesses_to_excel(businesses, str(output_file), region="NP")

    assert output_file.exists()

    workbook = load_workbook(output_file)
    worksheet = workbook.active

    assert worksheet.title == "Business Leads"

    assert worksheet.max_row == 3
    assert worksheet.max_column == 8

    assert worksheet["A1"].value == "Business Name"
    assert worksheet["B1"].value == "Address"
    assert worksheet["C1"].value == "Emails"
    assert worksheet["D1"].value == "Phone"
    assert worksheet["E1"].value == "Website"
    assert worksheet["F1"].value == "Category"
    assert worksheet["G1"].value == "Lead Score"
    assert worksheet["H1"].value == "Lead Quality"

    assert worksheet["A2"].value == "Nepal Hiking Team"
    assert worksheet["C2"].value == "info@nepalhikingteam.com"
    assert worksheet["D2"].value == "01-4989212"

    assert worksheet["C3"].value == (
        "info@nepaltrekkingexperts.com; sales@nepaltrekkingexperts.com"
    )

    # Verify lead scoring
    assert worksheet["G2"].value == 100
    assert worksheet["H2"].value == "High"

    assert worksheet["G3"].value == 100
    assert worksheet["H3"].value == "High"

    assert worksheet.freeze_panes == "A2"
    assert worksheet.auto_filter.ref == "A1:H3"

    workbook.close()


def test_export_empty_business_list(tmp_path):

    output_file = tmp_path / "empty_leads.xlsx"

    export_businesses_to_excel([], str(output_file))

    assert output_file.exists()

    workbook = load_workbook(output_file)
    worksheet = workbook.active

    assert worksheet.max_row == 1
    assert worksheet.max_column == 8
    assert worksheet["A1"].value == "Business Name"
    assert worksheet["C1"].value == "Emails"
    assert worksheet["G1"].value == "Lead Score"
    assert worksheet["H1"].value == "Lead Quality"

    workbook.close()


def test_export_business_without_emails(tmp_path):

    businesses = [
        Business(
            name="Example Adventures",
            emails=[],
        )
    ]

    output_file = tmp_path / "no_emails.xlsx"

    export_businesses_to_excel(businesses, str(output_file))

    workbook = load_workbook(output_file)
    worksheet = workbook.active

    assert worksheet["C2"].value is None
    assert worksheet["G2"].value == 0
    assert worksheet["H2"].value == "Low"

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

    export_businesses_to_excel([business], str(output_file))

    workbook = load_workbook(output_file)
    worksheet = workbook.active

    cell = worksheet["A2"]

    assert cell.value == malicious_value
    assert cell.data_type == "s"

    workbook.close()
