from enum import StrEnum


class LeadQuality(StrEnum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


def classify_lead_score(score: int) -> LeadQuality:
    if not isinstance(score, int) or isinstance(score, bool) or not 0 <= score <= 100:
        raise ValueError("Score must be an integer between 0 and 100.")

    if score >= 80:
        return LeadQuality.HIGH

    if score >= 50:
        return LeadQuality.MEDIUM

    return LeadQuality.LOW
