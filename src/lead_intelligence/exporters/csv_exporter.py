import csv

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.lead_scoring import LeadScoringService


def sanitize_csv_value(value):
    """Prevent spreadsheet applications from interpreting text as formulas."""
    if not isinstance(value, str):
        return value

    dangerous_prefixes = ("=", "+", "-", "@")
    normalized_value = value.lstrip(" \t\r\n\v\f")

    if normalized_value.startswith(dangerous_prefixes):
        return f"'{value}"

    return value


def export_businesses_to_csv(
    businesses: list[Business],
    output_path: str,
    region: str | None = None,
) -> None:
    scoring_service = LeadScoringService()

    headers = [
        "Business Name",
        "Address",
        "Emails",
        "Phone",
        "Website",
        "Category",
        "Lead Score",
        "Lead Quality",
    ]

    with open(
        output_path,
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.writer(csv_file)

        writer.writerow(headers)

        for business in businesses:
            score = scoring_service.score_business(business, region=region)
            quality = scoring_service.get_quality(score)

            values = [
                business.name,
                business.address,
                "; ".join(business.emails),
                ", ".join(business.phone_numbers),
                business.website,
                business.category,
                score,
                quality,
            ]

            writer.writerow([sanitize_csv_value(value) for value in values])

    print(f"CSV file exported successfully: {output_path}")
