from dataclasses import dataclass

from src.lead_intelligence.models.lead_quality import (
    LeadQuality,
    classify_lead_score,
)
from src.lead_intelligence.models.scoring_policy import MAX_SCORE, SCORING_VERSION


@dataclass(frozen=True, slots=True)
class ScoringResult:
    """Detailed breakdown of a business lead score."""

    email_points: int = 0
    phone_points: int = 0
    website_points: int = 0
    address_points: int = 0
    category_points: int = 0
    contact_bonus: int = 0
    policy_version: str = SCORING_VERSION
    sourced_email_count: int = 0
    sourced_phone_count: int = 0
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        values = (
            self.email_points,
            self.phone_points,
            self.website_points,
            self.address_points,
            self.category_points,
            self.contact_bonus,
            self.sourced_email_count,
            self.sourced_phone_count,
        )

        for value in values:
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("Score components must be non-negative integers.")

    @property
    def total_score(self) -> int:
        return min(
            MAX_SCORE,
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
