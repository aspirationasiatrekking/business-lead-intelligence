from src.lead_intelligence.services.business_search import BusinessSearchService
from src.lead_intelligence.exporters.excel_exporter import export_businesses_to_excel
from pathlib import Path



def main():

    input_query = input("Enter your search query: ")

    service = BusinessSearchService()
    businesses = service.search(input_query, country="np")
    export_businesses_to_excel(
    businesses,
    "output/business_leads.xlsx"
)

    print(f"\nFound {len(businesses)} businesses for query: '{input_query}'")

    for index, business in enumerate(businesses, start=1):
        print(f"\n--- Business {index} ---")
        print(f"Name: {business.name}")
        print(f"Address: {business.address}")
        print(f"Phone: {business.phone}")
        print(f"Website: {business.website}")
        print(f"Category: {business.category}")

  


if __name__ == "__main__":
    main()