import csv

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
)
from src.lead_intelligence.models.business import Business


def test_export_businesses_to_csv(tmp_path):
    businesses = [
        Business(
            name="Nepal Hiking Team",
            address="Thamel, Kathmandu",
            emails=["sales@example.com", "info@example.com"],
            phone_numbers=["+97714989212"],
            website="https://example.com",
            category="Travel agency",
        )
    ]

    output_file = tmp_path / "business_leads.csv"

    export_businesses_to_csv(businesses, str(output_file), region="NP")

    assert output_file.exists()

    with open(output_file, encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    assert rows[0] == [
        "Business Name",
        "Address",
        "Emails",
        "Phone",
        "Website",
        "Category",
        "Lead Score",
        "Lead Quality",
    ]

    assert rows[1][0] == "Nepal Hiking Team"
    assert rows[1][2] == "sales@example.com; info@example.com"
    assert rows[1][3] == "+97714989212"

    assert rows[1][6] == "100"
    assert rows[1][7] == "High"


def test_export_empty_business_list(tmp_path):
    output_file = tmp_path / "empty_leads.csv"

    export_businesses_to_csv([], str(output_file))

    assert output_file.exists()

    with open(output_file, encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    assert len(rows) == 1
    assert len(rows[0]) == 8
    assert rows[0][0] == "Business Name"
    assert rows[0][6] == "Lead Score"
    assert rows[0][7] == "Lead Quality"


def test_export_business_without_emails(tmp_path):
    businesses = [Business(name="Example Company")]

    output_file = tmp_path / "no_emails.csv"

    export_businesses_to_csv(businesses, str(output_file))

    with open(output_file, encoding="utf-8-sig", newline="") as file:
        rows = list(csv.reader(file))

    assert rows[1][2] == ""
    assert rows[1][6] == "0"
    assert rows[1][7] == "Low"
