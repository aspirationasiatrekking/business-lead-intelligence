from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import map_serper_places_with_report
from src.lead_intelligence.models.processing_result import SearchResult
from src.lead_intelligence.search.serper_provider import (
    SerperSearchProvider,
    is_google_redirect,
)
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)
from src.lead_intelligence.utils.country_utils import (
    normalize_country_code,
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
        """Return discovered businesses using the reporting search pipeline."""
        result = self.search_with_report(
            query=query,
            country=country,
            max_results=max_results,
        )

        return result.businesses

    def search_with_report(
        self,
        query: str,
        country: str | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> SearchResult:
        """Discover businesses and return detailed processing results."""
        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise TypeError("Maximum results must be an integer")

        if not 1 <= max_results <= self.MAX_ALLOWED_RESULTS:
            raise ValueError(
                f"Maximum results must be between 1 and {self.MAX_ALLOWED_RESULTS}"
            )
        country = normalize_country_code(country)

        results = self.provider.search_places(
            query=query,
            country=country,
            page=1,
            num=max_results,
        )

        places = results.get("places", [])

        has_redirects = any(
            isinstance(place, dict)
            and isinstance(place.get("website"), str)
            and is_google_redirect(place["website"])
            for place in places
        )

        if has_redirects:
            results = self.provider.resolve_links(results)
            places = results.get("places", [])

        region = country.upper() if country else None

        mapping_result = map_serper_places_with_report(
            places,
            region=region,
        )

        total_mapped = len(mapping_result.businesses)

        businesses = self.deduplication_service.deduplicate(mapping_result.businesses)

        duplicate_count = total_mapped - len(businesses)

        return SearchResult(
            businesses=businesses[:max_results],
            failures=mapping_result.failures,
            total_discovered=len(places),
            total_mapped=total_mapped,
            duplicate_count=duplicate_count,
        )
