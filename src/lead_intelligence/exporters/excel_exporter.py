from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.lead_scoring import LeadScoringService


def append_safe_row(worksheet, values: list) -> None:
    """Append values while ensuring untrusted strings are stored as text."""
    worksheet.append(values)

    for cell in worksheet[worksheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def export_businesses_to_excel(
    businesses: list[Business],
    output_path: str,
    region: str | None = None,
) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Business Leads"

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

    append_safe_row(worksheet, headers)

    for business in businesses:
        score = scoring_service.score_business(business, region=region)
        quality = scoring_service.get_quality(score)

        append_safe_row(
            worksheet,
            [
                business.name,
                business.address,
                "; ".join(business.emails),
                ", ".join(business.phone_numbers),
                business.website,
                business.category,
                score,
                quality,
            ],
        )

    for cell in worksheet[1]:
        cell.font = Font(
            bold=True,
            color="FFFFFF",
            size=12,
        )
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
        )

    for column in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        column_letter = get_column_letter(column[0].column)

        worksheet.column_dimensions[column_letter].width = min(
            max_length + 4,
            50,
        )

    worksheet.auto_filter.ref = worksheet.dimensions
    worksheet.freeze_panes = "A2"

    workbook.save(output_path)

    print(f"Excel file exported successfully: {output_path}")
