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

    # Search businesses and automatically close the HTTP session
    with BusinessSearchService() as search_service:
        businesses = search_service.search(
            input_query,
            country="np",
        )

    print(f"\nFound {len(businesses)} businesses.")

    contact_service = ContactDiscoveryService()
    scoring_service = LeadScoringService()

    for index, business in enumerate(businesses, start=1):
        print(f"\nProcessing {index}/{len(businesses)}: {business.name}")

        # Discover contact information
        if business.website:
            contact_service.discover(business, region="NP")

        # Calculate lead score after contact discovery
        score = scoring_service.score_business(business)
        quality = scoring_service.get_quality(score)

        print(f"Emails: {business.emails}")
        print(f"Phone numbers: {business.phone_numbers}")
        print(f"Lead Score: {score}/100")
        print(f"Lead Quality: {quality}")

    # Export results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    excel_path = output_dir / "business_leads.xlsx"
    csv_path = output_dir / "business_leads.csv"

    export_businesses_to_excel(
        businesses,
        str(excel_path),
        region="NP",
    )

    export_businesses_to_csv(
        businesses,
        str(csv_path),
        region="NP",
    )

    print(f"\nExported {len(businesses)} businesses.")
    print(f"Excel file: {excel_path}")
    print(f"CSV file: {csv_path}")


if __name__ == "__main__":
    main()
