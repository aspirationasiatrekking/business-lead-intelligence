import logging
from pathlib import Path
from tempfile import mkdtemp

from src.lead_intelligence.exporters.csv_exporter import (
    export_businesses_to_csv,
)
from src.lead_intelligence.exporters.excel_exporter import (
    export_businesses_to_excel,
)
from src.lead_intelligence.models.pipeline_progress import PipelineProgress
from src.lead_intelligence.models.search_request import (
    SearchRequest,
)
from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.services.lead_pipeline import LeadPipelineService
from src.lead_intelligence.settings import ApplicationSettings


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
    settings = ApplicationSettings.load(Path(__file__).resolve().parent / ".env")
    logging.basicConfig(
        level=settings.log_level, format="%(levelname)s %(name)s %(message)s"
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    request = read_search_request()

    print("\nSearch configuration")

    print(f"Country: {request.country_name} ({request.country_code})")

    print(f"City: {request.city}")
    print(f"Query: {request.query}")

    print(f"Search query: {request.search_query}")

    print(f"Maximum results: {request.max_results}")

    def report_progress(event: PipelineProgress) -> None:
        if event.stage == "searching":
            print("Searching for businesses...")
        elif event.stage == "processing":
            print(f"Processed {event.processed}/{event.total} businesses")

    pipeline = LeadPipelineService(
        search_factory=lambda: BusinessSearchService(settings=settings),
        contact_service=ContactDiscoveryService(settings),
    )
    result = pipeline.run(request, on_progress=report_progress)
    search_result = result.search_result
    businesses = result.businesses

    print("\nSearch report")

    print(f"Pages requested: {search_result.pages_requested}")

    print(f"Pages processed: {search_result.pages_processed}")

    print(f"Resolve requests: {search_result.resolve_requests}")
    print(f"Website search requests: {search_result.website_search_requests}")
    print(f"Website sources: {search_result.website_source_counts}")
    print(f"Website fallback outcomes: {search_result.website_fallback_outcomes}")
    print(f"Website candidate outcomes: {search_result.website_candidate_outcomes}")

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

    print(f"Pipeline duration: {result.duration_seconds:.2f}s")
    print(f"Businesses processed: {result.total_processed}")
    print(f"Businesses scored: {result.total_scored}")
    print(f"Extraction outcomes: {result.extraction_counts}")
    if result.is_partial:
        print("Warning: Pipeline completed with incomplete results.")
    for failure in result.failures:
        print(f"Processing failure: {failure.stage} ({failure.message})")
    for warning in result.warnings:
        print(f"Warning: {warning}")

    # Do not silently export an unscored record as a successful evaluation.
    businesses = [
        business for business in businesses if business.lead_score is not None
    ]
    omitted = result.total_processed - len(businesses)
    print(f"Unscored businesses omitted from exports: {omitted}")

    output_dir = settings.output_dir

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_dir = Path(mkdtemp(prefix="run-", dir=output_dir))
    excel_path = run_dir / "business_leads.xlsx"
    csv_path = run_dir / "business_leads.csv"

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
