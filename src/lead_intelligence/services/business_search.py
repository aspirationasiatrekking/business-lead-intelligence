from copy import deepcopy

import requests

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import (
    map_serper_places_with_report,
)
from src.lead_intelligence.models.processing_result import (
    SearchResult,
)
from src.lead_intelligence.models.search_request import (
    SearchRequest,
)
from src.lead_intelligence.search.serper_provider import (
    SerperResponseError,
    SerperSearchProvider,
    is_google_redirect,
)
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)
from src.lead_intelligence.utils.business_identity import normalize_serper_cid
from src.lead_intelligence.utils.country_utils import (
    normalize_country_code,
)


class BusinessSearchService:
    DEFAULT_MAX_RESULTS = SearchRequest.DEFAULT_MAX_RESULTS

    MAX_ALLOWED_RESULTS = SearchRequest.MAX_ALLOWED_RESULTS

    PAGE_SIZE = 10

    MAX_SEARCH_PAGES = 15

    MAX_NO_PROGRESS_PAGES = 2

    PROVIDER_ERRORS = (
        requests.exceptions.RequestException,
        SerperResponseError,
    )

    def __init__(self, provider=None):
        self.provider = provider if provider is not None else SerperSearchProvider()

        self.deduplication_service = BusinessDeduplicationService()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):
        self.close()

    def close(self):
        self.provider.close()

    @staticmethod
    def _record_credits(
        response: dict,
        result: SearchResult,
    ) -> None:
        """Record provider-reported credit usage."""

        credits = response.get("credits") if isinstance(response, dict) else None

        if isinstance(credits, int) and not isinstance(credits, bool) and credits >= 0:
            result.reported_credits += credits

        else:
            result.unknown_credit_responses += 1

    @staticmethod
    def _validate_query(query: str) -> str:
        if not isinstance(query, str):
            raise TypeError("Search query must be a string")

        query = query.strip()

        if not query:
            raise ValueError("Search query cannot be empty")

        return query

    @staticmethod
    def _validate_response(response: dict) -> list:
        if not isinstance(response, dict):
            raise SerperResponseError("Provider response must be a dictionary")

        places = response.get("places")

        if not isinstance(places, list):
            raise SerperResponseError("Provider places must be a list")

        return places

    @staticmethod
    def _has_google_redirects(
        places: list,
    ) -> bool:
        return any(
            isinstance(place, dict) and is_google_redirect(place.get("website"))
            for place in places
        )

    @staticmethod
    def _page_identity(
        places: list,
    ) -> tuple:
        """Create a page fingerprint without ranking positions."""

        identities = []

        for place in places:
            if not isinstance(place, dict):
                identities.append(repr(("invalid", place)))

                continue

            cid = normalize_serper_cid(place.get("cid"))

            if cid:
                identity = (
                    "cid",
                    cid,
                )

            else:
                identity = (
                    "fallback",
                    place.get("title"),
                    place.get("address"),
                    place.get("website"),
                    place.get("phoneNumber"),
                    place.get("category"),
                )

            identities.append(repr(identity))

        return tuple(sorted(identities))

    @staticmethod
    def _same_resolve_record(original: dict, resolved: object) -> bool:
        if not isinstance(resolved, dict):
            return False
        original_cid = normalize_serper_cid(original.get("cid"))
        resolved_cid = normalize_serper_cid(resolved.get("cid"))
        if original_cid or resolved_cid:
            return bool(original_cid and original_cid == resolved_cid)
        title = original.get("title")
        if not isinstance(title, str) or not title.strip():
            return False
        return all(
            original.get(key) == resolved.get(key)
            for key in ("title", "address", "phoneNumber", "position")
        )

    def _resolve_page(
        self,
        response: dict,
        places: list,
        result: SearchResult,
        page: int,
    ) -> list:
        """Resolve Google redirects when necessary."""

        if not self._has_google_redirects(places):
            return places

        # Avoid calling Resolve with malformed records.
        if any(not isinstance(place, dict) for place in places):
            result.warnings.append(
                f"Page {page}: redirect resolution "
                "skipped because records were malformed"
            )

            return places

        result.resolve_requests += 1
        credits_recorded = False

        try:
            resolved_response = self.provider.resolve_links(deepcopy(response))

            self._record_credits(
                resolved_response,
                result,
            )

            credits_recorded = True
            resolved_places = self._validate_response(resolved_response)

            if len(resolved_places) != len(places):
                result.warnings.append(
                    f"Page {page}: Resolve returned an unexpected number of records"
                )

                return places

            if not all(
                self._same_resolve_record(original, resolved)
                for original, resolved in zip(places, resolved_places, strict=True)
            ):
                result.warnings.append(f"Page {page}: Resolve identity mismatch")
                return places

            # Without CID, identical fallback identities cannot safely be aligned.
            cids = [
                cid
                for place in places
                if (cid := normalize_serper_cid(place.get("cid"))) is not None
            ]
            if len(set(cids)) != len(cids):
                result.warnings.append(f"Page {page}: ambiguous Resolve CIDs")
                return places

            fallback_keys = [
                tuple(
                    repr(place.get(key))
                    for key in ("title", "address", "phoneNumber", "position")
                )
                for place in places
                if normalize_serper_cid(place.get("cid")) is None
            ]
            if len(set(fallback_keys)) != len(fallback_keys):
                result.warnings.append(f"Page {page}: ambiguous Resolve identities")
                return places

            merged_places = []
            for original, resolved in zip(places, resolved_places, strict=True):
                merged = original.copy()
                if is_google_redirect(original.get("website")):
                    merged["website"] = resolved.get("website")
                merged_places.append(merged)
            return merged_places

        except self.PROVIDER_ERRORS as error:
            if not credits_recorded:
                result.unknown_credit_responses += 1
            result.warnings.append(
                f"Page {page}: redirect resolution failed ({type(error).__name__})"
            )

            return places

    def search_request(
        self,
        request: SearchRequest,
    ) -> SearchResult:
        if not isinstance(request, SearchRequest):
            raise TypeError("Expected a SearchRequest instance")

        result = self.search_with_report(
            query=request.search_query,
            country=request.provider_country,
            max_results=request.max_results,
        )

        result.request = request

        return result

    def search(
        self,
        query: str,
        country: str | None = None,
        max_results: int = DEFAULT_MAX_RESULTS,
    ) -> list[Business]:
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
        """Discover unique businesses across multiple pages."""

        query = self._validate_query(query)

        if not isinstance(max_results, int) or isinstance(max_results, bool):
            raise TypeError("Maximum results must be an integer")

        if not (1 <= max_results <= self.MAX_ALLOWED_RESULTS):
            raise ValueError(
                f"Maximum results must be between 1 and {self.MAX_ALLOWED_RESULTS}"
            )

        country = normalize_country_code(country)

        region = country.upper() if country else None

        result = SearchResult()

        mapped_businesses = []

        seen_pages = set()

        no_progress_pages = 0

        unique_businesses = []

        for page in range(
            1,
            self.MAX_SEARCH_PAGES + 1,
        ):
            result.pages_requested += 1
            credits_recorded = False

            try:
                response = self.provider.search_places(
                    query=query,
                    country=country,
                    page=page,
                    num=self.PAGE_SIZE,
                )

                self._record_credits(response, result)
                credits_recorded = True
                places = self._validate_response(response)

            except self.PROVIDER_ERRORS as error:
                if not credits_recorded:
                    result.unknown_credit_responses += 1
                # A failed first page is not an empty search.
                if result.pages_processed == 0:
                    raise

                result.warnings.append(
                    f"Page {page}: provider request failed ({type(error).__name__})"
                )

                result.stop_reason = "provider_error"

                break

            result.pages_processed += 1

            item_offset = result.total_discovered

            result.total_discovered += len(places)

            if not places:
                result.stop_reason = "empty_page"

                break

            page_identity = self._page_identity(places)

            if page_identity in seen_pages:
                result.stop_reason = "repeated_page"

                result.warnings.append(f"Page {page}: repeated provider results")

                break

            seen_pages.add(page_identity)

            places = self._resolve_page(
                response=response,
                places=places,
                result=result,
                page=page,
            )

            mapping_result = map_serper_places_with_report(
                places,
                region=region,
            )

            for failure in mapping_result.failures:
                failure.item_index += item_offset

                result.failures.append(failure)

            mapped_businesses.extend(mapping_result.businesses)

            result.total_mapped = len(mapped_businesses)

            previous_unique_count = len(unique_businesses)

            # Deduplication mutates Business records.
            # Preserve the original mapped records.
            unique_businesses = self.deduplication_service.deduplicate(
                deepcopy(mapped_businesses)
            )

            result.duplicate_count = result.total_mapped - len(unique_businesses)

            if len(unique_businesses) >= max_results:
                result.stop_reason = "result_limit_reached"

                break

            if len(unique_businesses) <= previous_unique_count:
                no_progress_pages += 1

            else:
                no_progress_pages = 0

            if no_progress_pages >= self.MAX_NO_PROGRESS_PAGES:
                result.stop_reason = "no_progress"

                break

        else:
            result.stop_reason = "page_budget_reached"

        result.businesses = unique_businesses[:max_results]

        return result
