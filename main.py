
from pathlib import Path

from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.services.contact_discovery import ContactDiscoveryService
from src.lead_intelligence.exporters.excel_exporter import export_businesses_to_excel


def main():

    input_query = input("Enter your search query: ")

    # Search businesses and automatically close the HTTP session
    with BusinessSearchService() as search_service:
        businesses = search_service.search(
            input_query,
            country="np",
        )

    print(f"\nFound {len(businesses)} businesses.")

    # Discover contact information
    contact_service = ContactDiscoveryService()

    for index, business in enumerate(businesses, start=1):

        print(f"\nProcessing {index}/{len(businesses)}: {business.name}")

        if business.website:
            contact_service.discover(business, region="NP")

        print(f"Emails: {business.emails}")
        print(f"Phone numbers: {business.phone_numbers}")

    # Export results
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    output_path = output_dir / "business_leads.xlsx"

    export_businesses_to_excel(
        businesses,
        str(output_path),
    )

    print(f"\nExported {len(businesses)} businesses.")
    print(f"File: {output_path}")


if __name__ == "__main__":
    main()
