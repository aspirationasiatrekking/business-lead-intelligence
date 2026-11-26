from pathlib import Path

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
)
from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.models.search_request import (
    SearchRequest,
)
from src.lead_intelligence.services.business_search import (
    BusinessSearchService,
)
from src.lead_intelligence.services.contact_discovery import (
    ContactDiscoveryService,
)
from src.lead_intelligence.services.lead_scoring import (
    LeadScoringService,
)


def read_search_request() -> SearchRequest:
    """Collect and validate a geographic search request."""

    while True:
        try:
            country_code = input("Enter country code (NP, US, GB, etc.): ")

            city = input("Enter city: ")

            query = input("Enter business search query: ")

            raw_max_results = input("Maximum results (1-100, default 10): ").strip()

            max_results = (
                int(raw_max_results)
                if raw_max_results
                else SearchRequest.DEFAULT_MAX_RESULTS
            )

            return SearchRequest(
                country_code=country_code,
                city=city,
                query=query,
                max_results=max_results,
            )

        except (ValueError, TypeError) as error:
            print(f"\nInvalid search request: {error}")

            print("Please enter the search details again.\n")


def main() -> None:
    request = read_search_request()

    print("\nSearch configuration")

    print(f"Country: {request.country_name} ({request.country_code})")

    print(f"City: {request.city}")
    print(f"Query: {request.query}")

    print(f"Search query: {request.search_query}")

    print(f"Maximum results: {request.max_results}")

    with BusinessSearchService() as search_service:
        search_result = search_service.search_request(request)

    businesses = search_result.businesses

    print("\nSearch report")

    print(f"Pages requested: {search_result.pages_requested}")

    print(f"Pages processed: {search_result.pages_processed}")

    print(f"Resolve requests: {search_result.resolve_requests}")

    print(f"Reported API credits: {search_result.reported_credits}")

    print(f"Responses with unknown credits: {search_result.unknown_credit_responses}")

    print(f"Search stop reason: {search_result.stop_reason}")

    if search_result.is_partial:
        print("Warning: Search results may be incomplete.")

    if search_result.warnings:
        print("\nSearch warnings:")

        for warning in search_result.warnings:
            print(f"- {warning}")

    print(f"Discovered: {search_result.total_discovered}")

    print(f"Mapped: {search_result.total_mapped}")

    print(f"Mapping failures: {search_result.total_failed}")

    print(f"Duplicates removed: {search_result.duplicate_count}")

    print(f"Businesses returned: {search_result.total_returned}")

    contact_service = ContactDiscoveryService()

    scoring_service = LeadScoringService()

    for index, business in enumerate(
        businesses,
        start=1,
    ):
        print(f"\nProcessing {index}/{len(businesses)}: {business.name}")

        region = business.country_code or request.phone_region

        contact_service.discover(
            business,
            region=region,
        )

        scoring_service.evaluate_business(
            business,
            region=region,
        )

        print(f"Address: {business.address}")

        print(f"Business city: {business.city or 'Unknown'}")

        print(f"Business country: {business.country or 'Unknown'}")

        print(f"Emails: {business.emails}")

        print(f"Phone numbers: {business.phone_numbers}")

        print(f"Extraction status: {business.extraction_status}")

        print(f"Source URLs: {business.source_urls}")

        print(f"Contact pages: {business.contact_page_urls}")

        print(f"Lead Score: {business.lead_score}/100")

        print(f"Lead Quality: {business.lead_quality}")

    output_dir = Path("output")

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    excel_path = output_dir / "business_leads.xlsx"

    csv_path = output_dir / "business_leads.csv"

    export_businesses_to_excel(
        businesses,
        str(excel_path),
        region=request.phone_region,
    )

    export_businesses_to_csv(
        businesses,
        str(csv_path),
        region=request.phone_region,
    )

    print(f"\nExported {len(businesses)} businesses.")

    print(f"Excel file: {excel_path}")
    print(f"CSV file: {csv_path}")


if __name__ == "__main__":
    main()
