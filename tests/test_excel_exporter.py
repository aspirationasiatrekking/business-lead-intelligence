
from openpyxl import load_workbook

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)


def test_export_businesses_to_excel(tmp_path):

    businesses = [
        Business(
            name="Nepal Hiking Team",
            address="Thamel, Kathmandu",
            phone="01-4989212",
            website="https://nepalhikingteam.com",
            category="Travel agency",
        ),
        Business(
            name="Nepal Trekking Experts",
            address="Kathmandu",
            phone="984-1917136",
            website="https://nepaltrekkingexperts.com",
            category="Tour agency",
        ),
    ]

    output_file = tmp_path / "business_leads.xlsx"

    export_businesses_to_excel(businesses, str(output_file))

    assert output_file.exists()

    workbook = load_workbook(output_file)
    worksheet = workbook.active

    assert worksheet.title == "Business Leads"

    assert worksheet.max_row == 3
    assert worksheet.max_column == 5

    assert worksheet["A1"].value == "Business Name"
    assert worksheet["B1"].value == "Address"
    assert worksheet["C1"].value == "Phone"
    assert worksheet["D1"].value == "Website"
    assert worksheet["E1"].value == "Category"

    assert worksheet["A2"].value == "Nepal Hiking Team"
    assert worksheet["C2"].value == "01-4989212"

    assert worksheet.freeze_panes == "A2"
    assert worksheet.auto_filter.ref == "A1:E3"

    workbook.close()


def test_export_empty_business_list(tmp_path):

    output_file = tmp_path / "empty_leads.xlsx"

    export_businesses_to_excel([], str(output_file))

    assert output_file.exists()

    workbook = load_workbook(output_file)
    worksheet = workbook.active

    assert worksheet.max_row == 1
    assert worksheet["A1"].value == "Business Name"

    workbook.close()
