from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import map_serper_places
from src.lead_intelligence.search.serper_provider import (
    SerperSearchProvider,
    is_google_redirect,
)
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)


class BusinessSearchService:
    DEFAULT_MAX_RESULTS = 10
    MAX_ALLOWED_RESULTS = 100

    def __init__(self, provider=None):
        self.provider = provider if provider is not None else SerperSearchProvider()
        self.deduplication_service = BusinessDeduplicationService()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
        self.provider.close()

    def search(
        self,
        query: str,
        country: str | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[Business]:
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise TypeError("Maximum results must be an integer")

        if not 1 <= max_results <= self.MAX_ALLOWED_RESULTS:
            raise ValueError(
                f"Maximum results must be between 1 and {self.MAX_ALLOWED_RESULTS}"
            )

        results = self.provider.search_places(
            query=query,
            country=country,
            page=1,
            num=max_results,
        )

        places = results.get("places", [])

        has_redirects = any(
            is_google_redirect(place.get("website")) for place in places
        )

        if has_redirects:
            results = self.provider.resolve_links(results)
            places = results.get("places", [])

        region = country.upper() if country else None

        businesses = map_serper_places(
            places,
            region=region,
        )

        businesses = self.deduplication_service.deduplicate(businesses)

        return businesses[:max_results]
