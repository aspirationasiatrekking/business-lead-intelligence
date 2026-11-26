from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.lead_quality import classify_lead_score
from src.lead_intelligence.services.lead_scoring import LeadScoringService

EXPORT_HEADERS = (
    "Business Name",
    "Address",
    "Emails",
    "Phone Numbers",
    "Website",
    "Category",
    "City",
    "District",
    "State",
    "Country",
    "Country Code",
    "Source URLs",
    "Contact Page URLs",
    "Extraction Status",
    "Lead Score",
    "Lead Quality",
)


def serialize_business(
    business: Business,
    scoring_service: LeadScoringService,
    region: str | None = None,
) -> list[str | int | None]:
    """Convert a business into the shared export row format."""
    score = business.lead_score

    if score is None:
        score = scoring_service.score_business(
            business,
            region=region,
        )

    quality = classify_lead_score(score)

    return [
        business.name,
        business.address,
        "; ".join(business.emails),
        ", ".join(business.phone_numbers),
        business.website,
        business.category,
        business.city,
        business.district,
        business.state,
        business.country,
        business.country_code,
        "; ".join(business.source_urls),
        "; ".join(business.contact_page_urls),
        business.extraction_status.value,
        score,
        quality.value,
    ]
