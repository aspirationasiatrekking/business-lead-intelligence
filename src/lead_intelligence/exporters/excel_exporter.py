
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from src.lead_intelligence.models.business import Business


def export_businesses_to_excel(
    businesses: list[Business],
    output_path: str
) -> None:

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Business Leads"

   
    headers = [
        "Business Name",
        "Address",
        "Phone",
        "Website",
        "Category",
    ]

    worksheet.append(headers)

    
    for business in businesses:
        worksheet.append([
            business.name,
            business.address,
            business.phone,
            business.website,
            business.category,
        ])

   
    for cell in worksheet[1]:
        cell.font = Font(
            bold=True,
            color="FFFFFF",
            size=12
        )
        cell.fill = PatternFill(
            fill_type="solid",
            fgColor="1F4E78"
        )
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center"
        )

    
    for column in worksheet.columns:
        max_length = max(
            len(str(cell.value or ""))
            for cell in column
        )

        column_letter = get_column_letter(column[0].column)
        worksheet.column_dimensions[column_letter].width = min(
            max_length + 4,
            50
        )

    
    worksheet.auto_filter.ref = worksheet.dimensions
    worksheet.freeze_panes = "A2"

    
    workbook.save(output_path)

    print(f"Excel file exported successfully: {output_path}")
