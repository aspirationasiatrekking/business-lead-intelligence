from src.lead_intelligence.extractors.contact_extractor import (
    extract_emails,
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.utils.url_utils import is_valid_website


class LeadScoringService:
    MAX_SCORE = 100

    @staticmethod
    def has_valid_email(emails: list[str]) -> bool:
        for email in emails:
            if extract_emails(email):
                return True

        return False

    @staticmethod
    def has_valid_phone(
        phone_numbers: list[str],
        region: str | None = None,
    ) -> bool:
        for phone in phone_numbers:
            if normalize_phone_number(phone, region=region):
                return True

        return False

    @staticmethod
    def has_valid_website(website: str | None) -> bool:
        if not website:
            return False

        return is_valid_website(website)

    def score_business(
        self,
        business: Business,
        region: str | None = None,
    ) -> int:
        score = 0

        valid_email = self.has_valid_email(business.emails)
        valid_phone = self.has_valid_phone(business.phone_numbers, region=region)
        valid_website = self.has_valid_website(business.website)

        if valid_email:
            score += 30

        if valid_phone:
            score += 20

        if valid_website:
            score += 15

        if business.address and business.address.strip():
            score += 10

        if business.category and business.category.strip():
            score += 10

        contact_methods = sum(
            [
                valid_email,
                valid_phone,
                valid_website,
            ]
        )

        if contact_methods >= 2:
            score += 15

        return min(score, self.MAX_SCORE)

    @staticmethod
    def get_quality(score: int) -> str:
        if (
            not isinstance(score, int)
            or isinstance(score, bool)
            or not 0 <= score <= 100
        ):
            raise ValueError("Score must be an integer between 0 and 100.")

        if score >= 80:
            return "High"

        if score >= 50:
            return "Medium"

        return "Low"
