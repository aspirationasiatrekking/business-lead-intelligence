from functools import lru_cache
from unicodedata import normalize

import pycountry

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.utils.country_utils import get_country_name


def text_key(value: str) -> str:
    return " ".join(normalize("NFKC", value).casefold().split())


# These names also commonly identify subnational locations.
AMBIGUOUS_COUNTRIES = frozenset({"georgia", "jersey", "guernsey"})
STATE_TYPES = frozenset({"state", "province", "region"})


@lru_cache(maxsize=1)
def country_names() -> dict[str, frozenset[str]]:
    names: dict[str, set[str]] = {}
    for country in pycountry.countries:
        for attr in ("name", "common_name", "official_name"):
            value = getattr(country, attr, None)
            if value:
                names.setdefault(text_key(value), set()).add(country.alpha_2)
    for alias, code in (("usa", "US"), ("uk", "GB")):
        names.setdefault(alias, set()).add(code)
    return {name: frozenset(codes) for name, codes in names.items()}


@lru_cache(maxsize=249)
def subdivision_names(code: str) -> dict[str, tuple[str, ...]]:
    names: dict[str, list[str]] = {}
    for item in pycountry.subdivisions.get(country_code=code) or []:
        if item.parent_code is None and item.type.casefold() in STATE_TYPES:
            names.setdefault(text_key(item.name), []).append(item.name)
    return {key: tuple(values) for key, values in names.items()}


class GeographicEnrichmentService:
    """Conservative, offline enrichment from explicit address components."""

    @staticmethod
    def _conflict(business: Business, message: str) -> None:
        if message not in business.geographic_conflicts:
            business.geographic_conflicts.append(message)

    @staticmethod
    def _fill(business: Business, field: str, value: str) -> None:
        if getattr(business, field) is None:
            setattr(business, field, value)
            business.geographic_sources.setdefault(field, []).append(
                "formatted_address"
            )
            if field == "country_code":
                business.lead_score = None

    def enrich(self, business: Business) -> Business:
        if not business.address or business.geographic_conflicts:
            return business
        parts = [part.strip() for part in business.address.split(",") if part.strip()]
        if len(parts) < 2:
            return business
        suffix = text_key(parts[-1])
        codes = country_names().get(suffix, frozenset())
        if len(codes) != 1 or suffix in AMBIGUOUS_COUNTRIES:
            return business
        code = next(iter(codes))
        if business.country_code and business.country_code != code:
            self._conflict(business, "Country code conflicts with formatted address")
            return business
        if business.country and code not in country_names().get(
            text_key(business.country), frozenset()
        ):
            self._conflict(business, "Country name conflicts with formatted address")
            return business
        self._fill(business, "country", get_country_name(code))
        self._fill(business, "country_code", code)
        # Only match the complete penultimate component, not street substrings.
        if len(parts) >= 3:
            names = subdivision_names(code).get(text_key(parts[-2]), ())
            if len(names) == 1:
                state = names[0]
                if business.state and text_key(business.state) != text_key(state):
                    self._conflict(business, "State conflicts with formatted address")
                else:
                    self._fill(business, "state", state)
        return business
