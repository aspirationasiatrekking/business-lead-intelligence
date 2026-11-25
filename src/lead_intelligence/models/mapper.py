from urllib.parse import urlparse

from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.processing_result import (
    MappingResult,
    ProcessingFailure,
)
from src.lead_intelligence.utils.url_utils import normalize_website_url


def map_serper_place(
    place: dict,
    region: str | None = None,
) -> Business | None:
    website = normalize_website_url(place.get("website"))

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

    phone_number = normalize_phone_number(
        place.get("phoneNumber"),
        region=region,
    )

    return Business(
        name=name,
        address=place.get("address"),
        phone_numbers=[phone_number] if phone_number else [],
        website=website,
        category=place.get("category"),
    )


def map_serper_places(
    places: list[dict],
    region: str | None = None,
) -> list[Business]:
    businesses = []

    for place in places:
        business = map_serper_place(place, region=region)

        if business is not None:
            businesses.append(business)

    return businesses


def map_serper_places_with_report(
    places: list[dict],
    region: str | None = None,
) -> MappingResult:
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

        business = map_serper_place(place, region=region)

        if business is None:
            result.failures.append(
                ProcessingFailure(
                    item_index=index,
                    stage="mapping",
                    message="Business has no usable name or valid website.",
                    item_name=place.get("title")
                    if isinstance(place.get("title"), str)
                    else None,
                )
            )
            continue

        result.businesses.append(business)

    return result
