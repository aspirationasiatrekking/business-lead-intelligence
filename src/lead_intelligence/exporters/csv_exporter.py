
import csv

from src.lead_intelligence.models.business import Business


def export_businesses_to_csv(
    businesses: list[Business],
    output_path: str,
) -> None:

    headers = [
        "Business Name",
        "Address",
        "Emails",
        "Phone",
        "Website",
        "Category",
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
            writer.writerow([
                business.name,
                business.address,
                "; ".join(business.emails),
                ", ".join(business.phone_numbers),
                business.website,
                business.category,
            ])

    print(f"CSV file exported successfully: {output_path}")
