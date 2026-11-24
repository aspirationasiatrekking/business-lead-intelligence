

from src.lead_intelligence.search.serper_provider import (SerperSearchProvider,is_google_redirect)
from src.lead_intelligence.models.mapper import map_serper_places
from src.lead_intelligence.models.business import Business



class BusinessSearchService:

    def __init__(self):
        self.provider = SerperSearchProvider()

    def search(self, query: str, country: str | None = None) -> list[Business]:
        results = self.provider.search_places(
            query=query,
            country=country
        )

        places = results.get("places", [])

        has_redirects = any(
            is_google_redirect(place.get("website"))
            for place in places
        )

        if has_redirects:
            results = self.provider.resolve_links(results)
            places = results.get("places", [])

        businesses = map_serper_places(places)

        return businesses
