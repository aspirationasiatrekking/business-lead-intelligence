from enum import StrEnum

from src.lead_intelligence.models.scoring_policy import (
    HIGH_THRESHOLD,
    MAX_SCORE,
    MEDIUM_THRESHOLD,
)


class LeadQuality(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


def classify_lead_score(score: int) -> LeadQuality:
    if (
        not isinstance(score, int)
        or isinstance(score, bool)
        or not 0 <= score <= MAX_SCORE
    ):
        raise ValueError("Score must be an integer between 0 and 100.")

    if score >= HIGH_THRESHOLD:
        return LeadQuality.HIGH

    if score >= MEDIUM_THRESHOLD:
        return LeadQuality.MEDIUM

    return LeadQuality.LOW
