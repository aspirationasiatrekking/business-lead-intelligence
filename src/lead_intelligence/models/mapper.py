
from src.lead_intelligence.utils.url_utils import normalize_website_url
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)


def map_serper_place(place: dict) -> Business:

    return Business(
        name=place.get("title"),
        address=place.get("address"),
        phone_numbers=(
        [normalized_phone]
        if (
            normalized_phone := normalize_phone_number(
            place.get("phoneNumber"),
            region="NP"
            )
            )
        else []
),
        website=normalize_website_url(place.get("website")),
        category=place.get("category"),
    )


def map_serper_places(places: list[dict]) -> list[Business]:
    return [map_serper_place(place) for place in places]
