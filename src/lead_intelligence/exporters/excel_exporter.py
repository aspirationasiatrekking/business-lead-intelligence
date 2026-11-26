from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from src.lead_intelligence.exporters.export_schema import (
    EXPORT_HEADERS,
    serialize_business,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.services.lead_scoring import LeadScoringService

MIN_COLUMN_WIDTH = 12
MAX_COLUMN_WIDTH = 50


def append_safe_row(
    worksheet,
    values: list | tuple,
) -> None:
    """Append values while storing untrusted strings as text."""
    worksheet.append(values)

    for cell in worksheet[worksheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def style_header(worksheet) -> None:
    """Apply consistent formatting to column headers."""
    for cell in worksheet[1]:
        cell.font = Font(
            bold=True,
            color="FFFFFF",
            size=11,
        )

        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78",
        )

        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True,
        )

    worksheet.row_dimensions[1].height = 30


def style_data_rows(worksheet) -> None:
    """Improve readability of exported business information."""
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(
                vertical="top",
                wrap_text=True,
            )

            if cell.row % 2 == 0:
                cell.fill = PatternFill(
                    fill_type="solid",
                    fgColor="F2F6FA",
                )

    score_column = EXPORT_HEADERS.index("Lead Score") + 1
    quality_column = EXPORT_HEADERS.index("Lead Quality") + 1

    quality_colors = {
        "High": "166534",
        "Medium": "92400E",
        "Low": "64748B",
    }

    for row_number in range(2, worksheet.max_row + 1):
        score_cell = worksheet.cell(
            row=row_number,
            column=score_column,
        )

        quality_cell = worksheet.cell(
            row=row_number,
            column=quality_column,
        )

        score_cell.alignment = Alignment(
            horizontal="center",
            vertical="top",
        )

        quality_cell.alignment = Alignment(
            horizontal="center",
            vertical="top",
        )

        quality_cell.font = Font(
            bold=True,
            color=quality_colors.get(
                quality_cell.value,
                "000000",
            ),
        )


def adjust_column_widths(worksheet) -> None:
    """Set readable and bounded worksheet column widths."""
    for column in worksheet.columns:
        max_length = max(
            len(str(cell.value if cell.value is not None else "")) for cell in column
        )

        column_letter = get_column_letter(column[0].column)

        worksheet.column_dimensions[column_letter].width = min(
            MAX_COLUMN_WIDTH,
            max(
                MIN_COLUMN_WIDTH,
                max_length + 4,
            ),
        )


def export_businesses_to_excel(
    businesses: list[Business],
    output_path: str,
    region: str | None = None,
) -> None:
    """Export business records to a formatted Excel workbook."""
    scoring_service = LeadScoringService()

    workbook = Workbook()

    try:
        worksheet = workbook.active
        worksheet.title = "Business Leads"

        append_safe_row(
            worksheet,
            EXPORT_HEADERS,
        )

        for business in businesses:
            values = serialize_business(
                business,
                scoring_service=scoring_service,
                region=region,
            )

            append_safe_row(
                worksheet,
                values,
            )

        style_header(worksheet)

        if businesses:
            style_data_rows(worksheet)

        adjust_column_widths(worksheet)

        worksheet.auto_filter.ref = worksheet.dimensions
        worksheet.freeze_panes = "A2"

        workbook.save(output_path)

    finally:
        workbook.close()

    print(f"Excel file exported successfully: {output_path}")
