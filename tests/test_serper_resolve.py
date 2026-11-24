
from src.lead_intelligence.search.serper_provider import SerperSearchProvider

provider = SerperSearchProvider()

results = provider.search_places(
    query="Trekking companies in Nepal",
    country="np"
)

resolved = provider.resolve_links(results)

for place in resolved.get("places", []):
    print(f"\nBusiness: {place.get('title')}")
    print(f"Website: {place.get('website')}")
