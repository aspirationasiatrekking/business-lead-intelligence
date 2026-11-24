
from src.lead_intelligence.search.serper_provider import SerperSearchProvider


provider = SerperSearchProvider()

results = provider.search_places(
    query="Trekking companies in Nepal",
    country="np"
)


from urllib.parse import urlparse

places = results.get("places", [])

print(f"\nTotal businesses: {len(places)}")

print("\n--- FIELD AVAILABILITY ---")

fields = [
    "title",
    "address",
    "phoneNumber",
    "website",
    "category",
    "rating",
    "ratingCount",
    "cid"
]

for field in fields:
    available = sum(
        1 for place in places
        if place.get(field) is not None
    )

    print(f"{field}: {available}/{len(places)}")

print("\n--- RAW WEBSITE URLS ---")

for place in places:
    print(f"\nBusiness: {place.get('title')}")
    print(f"Website: {place.get('website')}")
    print(f"Link: {place.get('link')}")


