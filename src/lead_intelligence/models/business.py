from dataclasses import dataclass, field

from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.lead_quality import (
    LeadQuality,
    classify_lead_score,
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

        list_fields = (
            "emails",
            "phone_numbers",
            "source_urls",
            "contact_page_urls",
        )

        for field_name in list_fields:
            values = getattr(self, field_name)

            if not isinstance(values, list):
                raise TypeError(f"{field_name} must be a list.")

            if not all(isinstance(value, str) for value in values):
                raise TypeError(f"{field_name} must contain only strings.")

            # Prevent sharing caller-owned mutable lists.
            setattr(self, field_name, values.copy())

        self.extraction_status = ExtractionStatus(self.extraction_status)

        if self.lead_score is not None:
            classify_lead_score(self.lead_score)

    @property
    def lead_quality(self) -> LeadQuality | None:
        if self.lead_score is None:
            return None

        return classify_lead_score(self.lead_score)
