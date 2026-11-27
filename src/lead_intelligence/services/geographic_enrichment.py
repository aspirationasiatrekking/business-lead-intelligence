import re
from dataclasses import dataclass
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt
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


# GeoNames data (CC BY 4.0): https://www.geonames.org/
CITY_SOURCE = "geonames_address_coordinates"
MAX_CITY_DISTANCE_KM = 10.0
POSTCODE_SUFFIX = re.compile(r" [0-9]{3,10}$")


@dataclass(frozen=True, slots=True)
class CityPoint:
    name: str
    country_code: str
    latitude: float
    longitude: float


@lru_cache(maxsize=1)
def city_index() -> dict[str, tuple[CityPoint, ...]]:
    # Load once per process, only when coordinate-based enrichment is needed.
    from geonamescache import GeonamesCache

    index: dict[str, list[CityPoint]] = {}
    for city in GeonamesCache().get_cities().values():
        code = city["countrycode"]
        if pycountry.countries.get(alpha_2=code) is None:
            continue
        point = CityPoint(
            city["name"], code, float(city["latitude"]), float(city["longitude"])
        )
        index.setdefault(text_key(point.name), []).append(point)
    return {key: tuple(points) for key, points in index.items()}


def distance_km(lat: float, lon: float, point: CityPoint) -> float:
    latitude_delta = radians(point.latitude - lat)
    longitude_delta = radians(point.longitude - lon)
    a = sin(latitude_delta / 2) ** 2 + (
        cos(radians(lat)) * cos(radians(point.latitude)) * sin(longitude_delta / 2) ** 2
    )
    return 6371.0088 * 2 * asin(sqrt(max(0.0, min(1.0, a))))


def match_city(business: Business) -> CityPoint | None:
    if not business.address or business.latitude is None or business.longitude is None:
        return None
    parts = [text_key(part) for part in business.address.split(",") if part.strip()]
    if parts and parts[-1] in country_names():
        parts.pop()
    if not parts:
        return None
    index = city_index()
    matches = set()
    for part in parts[-3:]:
        # Never match arbitrary substrings, business titles or requested locations.
        for key in {part, POSTCODE_SUFFIX.sub("", part)}:
            for point in index.get(key, ()):
                if distance_km(business.latitude, business.longitude, point) <= (
                    MAX_CITY_DISTANCE_KM
                ):
                    matches.add(point)
    return next(iter(matches)) if len(matches) == 1 else None


class GeographicEnrichmentService:
    """Conservative offline enrichment from address and coordinate evidence."""

    @staticmethod
    def _conflict(business: Business, message: str) -> None:
        if message not in business.geographic_conflicts:
            business.geographic_conflicts.append(message)

    @staticmethod
    def _fill(
        business: Business, field: str, value: str, source: str = "formatted_address"
    ) -> None:
        if getattr(business, field) is None:
            setattr(business, field, value)
            business.geographic_sources.setdefault(field, []).append(source)
            if field == "country_code":
                business.invalidate_score()

    def _enrich_address(self, business: Business) -> Business:
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

    def enrich(self, business: Business) -> Business:
        self._enrich_address(business)
        if business.geographic_conflicts or (
            business.city and business.country and business.country_code
        ):
            return business
        point = match_city(business)
        if point is None:
            return business
        if business.country_code and business.country_code != point.country_code:
            self._conflict(
                business, "Country code conflicts with city-coordinate match"
            )
            return business
        if business.country and point.country_code not in country_names().get(
            text_key(business.country), frozenset()
        ):
            self._conflict(
                business, "Country name conflicts with city-coordinate match"
            )
            return business
        if business.city and text_key(business.city) != text_key(point.name):
            # Suburbs and municipal names can legitimately differ: abstain.
            return business
        self._fill(business, "city", point.name, CITY_SOURCE)
        self._fill(
            business, "country", get_country_name(point.country_code), CITY_SOURCE
        )
        self._fill(business, "country_code", point.country_code, CITY_SOURCE)
        return business
