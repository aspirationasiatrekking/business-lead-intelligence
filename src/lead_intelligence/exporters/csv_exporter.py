import csv

from src.lead_intelligence.exporters.export_schema import (
    EXPORT_HEADERS,
    serialize_business,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.lead_scoring import LeadScoringService


def sanitize_csv_value(value):
    """Prevent spreadsheet applications from interpreting text as formulas."""
    if not isinstance(value, str):
        return value

    dangerous_prefixes = (
        "=",
        "+",
        "-",
        "@",
        "＝",
        "＋",
        "－",
        "＠",
    )

    normalized_value = value.lstrip()

    if value.startswith(("\t", "\r", "\n")) or normalized_value.startswith(
        dangerous_prefixes
    ):
        return f"'{value}"

    return value


def export_businesses_to_csv(
    businesses: list[Business],
    output_path: str,
    region: str | None = None,
) -> None:
    """Export business records to a UTF-8 CSV file."""
    scoring_service = LeadScoringService()

    with open(
        output_path,
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.writer(
            csv_file,
            quoting=csv.QUOTE_ALL,
        )

        writer.writerow(EXPORT_HEADERS)

        for business in businesses:
            values = serialize_business(
                business,
                scoring_service=scoring_service,
                region=region,
            )

            writer.writerow([sanitize_csv_value(value) for value in values])

    print(f"CSV file exported successfully: {output_path}")
