import csv

import pytest

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
    sanitize_csv_value,
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


def read_csv(path):
    with open(
        path,
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.reader(file))


def test_export_businesses_to_csv(tmp_path):
    businesses = [
        Business(
            name="Nepal Hiking Team",
            address="Thamel, Kathmandu",
            emails=[
                "sales@example.com",
                "info@example.com",
            ],
            phone_numbers=["+97714989212"],
            website="https://example.com",
            category="Travel agency",
        )
    ]

    output_file = tmp_path / "business_leads.csv"

    export_businesses_to_csv(
        businesses,
        str(output_file),
        region="NP",
    )

    assert output_file.exists()

    rows = read_csv(output_file)

    assert rows[0] == EXPECTED_HEADERS
    assert len(rows[1]) == 16

    assert rows[1][0] == "Nepal Hiking Team"
    assert rows[1][2] == "sales@example.com; info@example.com"
    assert rows[1][3] == "'+97714989212"

    assert rows[1][13] == "pending"
    assert rows[1][14] == "100"
    assert rows[1][15] == "High"


def test_export_empty_business_list(tmp_path):
    output_file = tmp_path / "empty_leads.csv"

    export_businesses_to_csv(
        [],
        str(output_file),
    )

    rows = read_csv(output_file)

    assert rows == [EXPECTED_HEADERS]


def test_export_business_without_emails(tmp_path):
    businesses = [Business(name="Example Company")]

    output_file = tmp_path / "no_emails.csv"

    export_businesses_to_csv(
        businesses,
        str(output_file),
    )

    rows = read_csv(output_file)

    assert rows[1][2] == ""
    assert rows[1][14] == "0"
    assert rows[1][15] == "Low"


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
def test_export_formula_like_business_names_safely(
    tmp_path,
    malicious_value,
):
    business = Business(name=malicious_value)

    output_file = tmp_path / "formula_injection.csv"

    export_businesses_to_csv(
        [business],
        str(output_file),
    )

    rows = read_csv(output_file)

    assert rows[1][0] == (f"'{malicious_value.strip()}")


def test_export_formula_like_values_in_multiple_fields(
    tmp_path,
):
    business = Business(
        name="Example Company",
        address="=HYPERLINK('https://example.com')",
        emails=["=malicious@example.com"],
        category="@SUM(A1:A2)",
    )

    output_file = tmp_path / "formula_fields.csv"

    export_businesses_to_csv(
        [business],
        str(output_file),
    )

    rows = read_csv(output_file)

    assert rows[1][1] == "'=HYPERLINK('https://example.com')"
    assert rows[1][2] == "'=malicious@example.com"
    assert rows[1][5] == "'@SUM(A1:A2)"


@pytest.mark.parametrize(
    "malicious_value",
    [
        "  =1+1",
        "\t=1+1",
        "\n=1+1",
    ],
)
def test_csv_export_handles_unnormalized_formula_values(
    tmp_path,
    malicious_value,
):
    business = Business(name="Example Business")

    business.name = malicious_value

    output_file = tmp_path / "unsafe_value.csv"

    export_businesses_to_csv(
        [business],
        str(output_file),
    )

    rows = read_csv(output_file)

    assert rows[1][0] == f"'{malicious_value}"


@pytest.mark.parametrize(
    "value",
    [
        "＝1+1",
        "＋1+1",
        "－1+1",
        "＠SUM(A1:A2)",
        "\tExample",
        "\rExample",
        "\nExample",
        "\u00a0=1+1",
    ],
)
def test_csv_sanitizer_handles_additional_dangerous_prefixes(
    value,
):
    assert sanitize_csv_value(value) == f"'{value}"


@pytest.mark.parametrize(
    "value",
    [
        None,
        0,
        100,
        "",
        "Example Business",
        "info@example.com",
        "https://example.com",
    ],
)
def test_csv_sanitizer_preserves_safe_values(value):
    assert sanitize_csv_value(value) == value


def test_csv_export_uses_utf8_bom(tmp_path):
    output_file = tmp_path / "unicode.csv"

    business = Business(
        name="नेपाल ट्रेकिङ",
    )

    export_businesses_to_csv(
        [business],
        str(output_file),
    )

    assert output_file.read_bytes().startswith(b"\xef\xbb\xbf")

    rows = read_csv(output_file)

    assert rows[1][0] == "नेपाल ट्रेकिङ"


def test_csv_export_preserves_commas_quotes_and_newlines(
    tmp_path,
):
    business = Business(
        name='Example, "Travel" Company',
        address="Street 1\nKathmandu, Nepal",
    )

    output_file = tmp_path / "special_characters.csv"

    export_businesses_to_csv(
        [business],
        str(output_file),
    )

    rows = read_csv(output_file)

    assert len(rows) == 2
    assert len(rows[1]) == 16

    assert rows[1][0] == 'Example, "Travel" Company'
    assert rows[1][1] == "Street 1\nKathmandu, Nepal"
