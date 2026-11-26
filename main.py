from pathlib import Path

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
)
from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.services.lead_scoring import LeadScoringService


def main():
    input_query = input("Enter your search query: ")

    country = "np"
    region = country.upper()

    # Discover businesses and preserve mapping reports.
    with BusinessSearchService() as search_service:
        search_result = search_service.search_with_report(
            input_query,
            country=country,
        )

    businesses = search_result.businesses

    print("\nSearch report")
    print(f"Discovered: {search_result.total_discovered}")
    print(f"Mapped: {search_result.total_mapped}")
    print(f"Mapping failures: {search_result.total_failed}")
    print(f"Duplicates removed: {search_result.duplicate_count}")
    print(f"Businesses returned: {search_result.total_returned}")

    contact_service = ContactDiscoveryService()
    scoring_service = LeadScoringService()

    for index, business in enumerate(businesses, start=1):
        print(f"\nProcessing {index}/{len(businesses)}: {business.name}")

        # Always run discovery so missing websites receive a status.
        contact_service.discover(
            business,
            region=region,
        )

        # Evaluate and store the score on the business.
        scoring_service.evaluate_business(
            business,
            region=region,
        )

        print(f"Emails: {business.emails}")
        print(f"Phone numbers: {business.phone_numbers}")
        print(f"Extraction status: {business.extraction_status}")
        print(f"Source URLs: {business.source_urls}")
        print(f"Contact pages: {business.contact_page_urls}")
        print(f"Lead Score: {business.lead_score}/100")
        print(f"Lead Quality: {business.lead_quality}")

    # Export results.
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    excel_path = output_dir / "business_leads.xlsx"
    csv_path = output_dir / "business_leads.csv"

    export_businesses_to_excel(
        businesses,
        str(excel_path),
        region=region,
    )

    export_businesses_to_csv(
        businesses,
        str(csv_path),
        region=region,
    )

    print(f"\nExported {len(businesses)} businesses.")
    print(f"Excel file: {excel_path}")
    print(f"CSV file: {csv_path}")


if __name__ == "__main__":
    main()
