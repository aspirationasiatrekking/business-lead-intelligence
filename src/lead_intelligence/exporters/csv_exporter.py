import csv
from unicodedata import category, normalize

from src.lead_intelligence.exporters.atomic_output import atomic_output
from src.lead_intelligence.exporters.export_schema import (
    EXPORT_HEADERS,
    serialize_business,
)
from src.lead_intelligence.exporters.export_validation import validate_export_text
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.lead_scoring import LeadScoringService


def sanitize_csv_value(value):
    """Prevent spreadsheet applications from interpreting text as formulas."""
    if not isinstance(value, str):
        return value

    validate_export_text(value)
    # Inspect compatibility-normalized text, but preserve original cell contents.
    normalized = normalize("NFKC", value)
    index = 0
    suspicious_prefix = False
    for char in normalized:
        if not (char.isspace() or category(char) == "Cf"):
            break
        if char in "\t\r\n" or category(char) == "Cf":
            suspicious_prefix = True
        index += 1

    if suspicious_prefix or normalized[index:].startswith(("=", "+", "-", "@")):
        return f"'{value}"

    return value


def export_businesses_to_csv(
    businesses: list[Business],
    output_path: str,
    region: str | None = None,
    *,
    overwrite: bool = False,
) -> None:
    """Export business records to a UTF-8 CSV file."""
    scoring_service = LeadScoringService()

    with atomic_output(output_path, ".csv", overwrite=overwrite) as temporary_path:
        with open(
            temporary_path,
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
