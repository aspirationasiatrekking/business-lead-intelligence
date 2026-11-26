from urllib.parse import urlparse

from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.processing_result import (
    MappingResult,
    ProcessingFailure,
)
from src.lead_intelligence.search.serper_provider import is_google_redirect
from src.lead_intelligence.services.geographic_enrichment import (
    GeographicEnrichmentService,
)
from src.lead_intelligence.utils.business_identity import (
    normalize_coordinate,
    normalize_serper_cid,
)
from src.lead_intelligence.utils.country_utils import (
    find_country_code,
    get_country_name,
    validate_country_code,
)
from src.lead_intelligence.utils.url_utils import normalize_website_url
from src.lead_intelligence.utils.website_policy import is_candidate_business_website


def get_optional_text(value) -> str | None:
    """Return optional geographic text without inventing data."""

    if not isinstance(value, str):
        return None

    return value.strip() or None


def extract_geographic_fields(
    place: dict,
) -> dict[str, str | None]:
    """Map explicitly supplied geographic information."""

    city = get_optional_text(place.get("city"))

    district = get_optional_text(place.get("district"))

    state = get_optional_text(place.get("state"))

    country = get_optional_text(place.get("country"))

    raw_country_code = get_optional_text(place.get("countryCode"))

    country_code = None

    if raw_country_code:
        try:
            country_code = validate_country_code(raw_country_code)

        except ValueError:
            country_code = None

    name_country_code = find_country_code(country)

    if (
        country_code is not None
        and name_country_code is not None
        and country_code != name_country_code
    ):
        # Conflicting location evidence.
        # Do not arbitrarily select one country.
        country = None
        country_code = None

    else:
        country_code = country_code or name_country_code

        if country_code:
            country = get_country_name(country_code)

    return {
        "city": city,
        "district": district,
        "state": state,
        "country": country,
        "country_code": country_code,
    }


def map_serper_place(
    place: dict,
    region: str | None = None,
) -> Business | None:
    """Map an individual Serper place into a Business record."""

    raw_website = place.get("website")
    website = (
        normalize_website_url(raw_website)
        if is_candidate_business_website(raw_website)
        else None
    )

    name = place.get("title")

    if isinstance(name, str):
        name = name.strip()

    else:
        name = None

    if not name and website:
        hostname = urlparse(website).hostname

        if hostname:
            name = hostname.removeprefix("www.")

    if not name:
        return None

    geographic_fields = extract_geographic_fields(place)

    # Preserve a provider contradiction before the normalized fields lose it.
    raw_code = get_optional_text(place.get("countryCode"))
    raw_name = find_country_code(get_optional_text(place.get("country")))
    conflicts = []
    if raw_code and raw_name:
        try:
            valid_code = validate_country_code(raw_code)
        except ValueError:
            valid_code = None
        if valid_code and valid_code != raw_name:
            conflicts.append("Provider country name and code disagree")

    business = Business(
        name=name,
        address=place.get("address"),
        website=website,
        website_status=(
            "accepted"
            if website
            else "unresolved_redirect"
            if is_google_redirect(raw_website)
            else "rejected"
            if raw_website
            else "missing"
        ),
        website_source=(place.get("_website_source", "places") if website else None),
        category=place.get("category"),
        serper_cid=normalize_serper_cid(place.get("cid")),
        latitude=normalize_coordinate(place.get("latitude"), 90),
        longitude=normalize_coordinate(place.get("longitude"), 180),
        geographic_sources={
            key: ["provider"] for key, value in geographic_fields.items() if value
        },
        geographic_conflicts=conflicts,
        **geographic_fields,
    )
    GeographicEnrichmentService().enrich(business)
    phone_number = normalize_phone_number(
        place.get("phoneNumber"), region=business.country_code or region
    )
    business.phone_numbers = [phone_number] if phone_number else []
    return business


def map_serper_places_with_report(
    places: list[dict],
    region: str | None = None,
) -> MappingResult:
    """Map business records while isolating individual failures."""
    result = MappingResult()

    for index, place in enumerate(places):
        if not isinstance(place, dict):
            result.failures.append(
                ProcessingFailure(
                    item_index=index,
                    stage="mapping",
                    message="Expected a dictionary for the business record.",
                )
            )
            continue

        item_name = place.get("title")

        if not isinstance(item_name, str):
            item_name = None

        try:
            business = map_serper_place(
                place,
                region=region,
            )

            if business is None:
                result.failures.append(
                    ProcessingFailure(
                        item_index=index,
                        stage="mapping",
                        message="Business has no usable name or valid website.",
                        item_name=item_name,
                    )
                )
                continue

            result.businesses.append(business)

        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            result.failures.append(
                ProcessingFailure(
                    item_index=index,
                    stage="mapping",
                    message=f"{type(exc).__name__}: {exc}",
                    item_name=item_name,
                )
            )

    return result


def map_serper_places(
    places: list[dict],
    region: str | None = None,
) -> list[Business]:
    """Map business records using the failure-isolated batch mapper."""
    result = map_serper_places_with_report(
        places,
        region=region,
    )

    return result.businesses
