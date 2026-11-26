from dataclasses import dataclass

from src.lead_intelligence.models.lead_quality import (
    LeadQuality,
    classify_lead_score,
)


@dataclass(frozen=True, slots=True)
class ScoringResult:
    """Detailed breakdown of a business lead score."""

    email_points: int = 0
    phone_points: int = 0
    website_points: int = 0
    address_points: int = 0
    category_points: int = 0
    contact_bonus: int = 0

    def __post_init__(self) -> None:
        values = (
            self.email_points,
            self.phone_points,
            self.website_points,
            self.address_points,
            self.category_points,
            self.contact_bonus,
        )

        for value in values:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("Score components must be non-negative integers.")

    @property
    def total_score(self) -> int:
        return min(
            100,
            self.email_points
            + self.phone_points
            + self.website_points
            + self.address_points
            + self.category_points
            + self.contact_bonus,
        )

    @property
    def quality(self) -> LeadQuality:
        return classify_lead_score(self.total_score)
