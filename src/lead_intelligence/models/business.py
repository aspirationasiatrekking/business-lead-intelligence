from dataclasses import dataclass, field

from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.lead_quality import (
    LeadQuality,
    classify_lead_score,
)
from src.lead_intelligence.utils.business_identity import (
    normalize_coordinate,
    normalize_serper_cid,
)


@dataclass
class Business:
    name: str
    address: str | None = None
    emails: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    website: str | None = None
    category: str | None = None

    # Geographic information
    city: str | None = None
    district: str | None = None
    state: str | None = None
    country: str | None = None
    country_code: str | None = None

    # Source tracking
    source_urls: list[str] = field(default_factory=list)
    contact_page_urls: list[str] = field(default_factory=list)

    # Extraction information
    extraction_status: ExtractionStatus = ExtractionStatus.PENDING

    # Lead scoring
    lead_score: int | None = None

    # Provider identity and optional geographic coordinates.
    serper_cid: str | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Website evidence keyed by normalized email or E.164 number.
    email_sources: dict[str, list[str]] = field(default_factory=dict)
    phone_sources: dict[str, list[str]] = field(default_factory=dict)

    # Evidence for geographic fields and unresolved contradictions.
    geographic_sources: dict[str, list[str]] = field(default_factory=dict)
    geographic_conflicts: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("Business name must be a string.")

        self.name = self.name.strip()

        if not self.name:
            raise ValueError("Business name must not be empty.")

        optional_text_fields = (
            "address",
            "website",
            "category",
            "city",
            "district",
            "state",
            "country",
            "country_code",
        )

        for field_name in optional_text_fields:
            value = getattr(self, field_name)

            if value is None:
                continue

            if not isinstance(value, str):
                raise TypeError(f"{field_name} must be a string or None.")

            setattr(self, field_name, value.strip() or None)

        if self.country_code is not None:
            if (
                len(self.country_code) != 2
                or not self.country_code.isascii()
                or not self.country_code.isalpha()
            ):
                raise ValueError("Country code must contain two ASCII letters.")

            self.country_code = self.country_code.upper()

        if self.serper_cid is not None:
            cid = normalize_serper_cid(self.serper_cid)
            if cid is None:
                raise ValueError("Invalid Serper CID.")
            self.serper_cid = cid

        for field_name, limit in (("latitude", 90), ("longitude", 180)):
            value = getattr(self, field_name)
            if value is not None:
                coordinate = normalize_coordinate(value, limit)
                if coordinate is None:
                    raise ValueError(f"Invalid {field_name}.")
                setattr(self, field_name, coordinate)

        list_fields = (
            "emails",
            "phone_numbers",
            "source_urls",
            "contact_page_urls",
            "geographic_conflicts",
        )

        for field_name in list_fields:
            values = getattr(self, field_name)

            if not isinstance(values, list):
                raise TypeError(f"{field_name} must be a list.")

            if not all(isinstance(value, str) for value in values):
                raise TypeError(f"{field_name} must contain only strings.")

            # Prevent sharing caller-owned mutable lists.
            setattr(self, field_name, values.copy())

        for field_name in ("email_sources", "phone_sources", "geographic_sources"):
            sources = getattr(self, field_name)
            if not isinstance(sources, dict):
                raise TypeError(f"{field_name} must be a dictionary.")
            copied = {}
            for key, urls in sources.items():
                if not isinstance(key, str) or not key.strip():
                    raise ValueError("Contact source key must be nonempty text.")
                if not isinstance(urls, list) or not all(
                    isinstance(url, str) for url in urls
                ):
                    raise TypeError("Contact sources must be lists of strings.")
                copied[key] = list(dict.fromkeys(urls))
            setattr(self, field_name, copied)

        self.extraction_status = ExtractionStatus(self.extraction_status)

        if self.lead_score is not None:
            classify_lead_score(self.lead_score)

    @property
    def lead_quality(self) -> LeadQuality | None:
        if self.lead_score is None:
            return None

        return classify_lead_score(self.lead_score)
