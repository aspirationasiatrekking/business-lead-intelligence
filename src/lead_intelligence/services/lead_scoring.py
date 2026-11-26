from email_validator import EmailNotValidError, validate_email

from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.lead_quality import (
    LeadQuality,
    classify_lead_score,
)
from src.lead_intelligence.models.scoring_result import ScoringResult
from src.lead_intelligence.utils.country_utils import normalize_country_code
from src.lead_intelligence.utils.url_utils import is_valid_website


class LeadScoringService:
    MAX_SCORE = 100

    EMAIL_POINTS = 30
    PHONE_POINTS = 20
    WEBSITE_POINTS = 15
    ADDRESS_POINTS = 10
    CATEGORY_POINTS = 10
    MULTIPLE_CONTACT_BONUS = 15

    @staticmethod
    def has_valid_email(emails: list[str]) -> bool:
        """Check whether at least one complete email is valid."""
        for email in emails:
            if not isinstance(email, str):
                continue

            email = email.strip()

            if not email:
                continue

            try:
                validate_email(
                    email,
                    check_deliverability=False,
                )

                return True

            except EmailNotValidError:
                continue

        return False

    @staticmethod
    def has_valid_phone(
        phone_numbers: list[str],
        region: str | None = None,
    ) -> bool:
        """Check whether at least one valid phone number exists."""
        normalized_region = normalize_country_code(region)

        if normalized_region is not None:
            normalized_region = normalized_region.upper()

        for phone in phone_numbers:
            if normalize_phone_number(
                phone,
                region=normalized_region,
            ):
                return True

        return False

    @staticmethod
    def has_valid_website(website: str | None) -> bool:
        """Check whether a syntactically valid website exists."""
        if not isinstance(website, str):
            return False

        return is_valid_website(website)

    @staticmethod
    def _has_text(value: str | None) -> bool:
        """Check whether a field contains meaningful text."""
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _resolve_region(
        business: Business,
        region: str | None,
    ) -> str | None:
        """Prefer known business geography over search context."""
        selected_region = (
            business.country_code if business.country_code is not None else region
        )

        normalized_region = normalize_country_code(selected_region)

        if normalized_region is None:
            return None

        return normalized_region.upper()

    def score_with_breakdown(
        self,
        business: Business,
        region: str | None = None,
    ) -> ScoringResult:
        """Calculate a detailed score without modifying the business."""
        selected_region = self._resolve_region(
            business,
            region,
        )

        valid_email = self.has_valid_email(business.emails)

        valid_phone = self.has_valid_phone(
            business.phone_numbers,
            region=selected_region,
        )

        valid_website = self.has_valid_website(business.website)

        contact_methods = sum(
            (
                valid_email,
                valid_phone,
                valid_website,
            )
        )

        return ScoringResult(
            email_points=(self.EMAIL_POINTS if valid_email else 0),
            phone_points=(self.PHONE_POINTS if valid_phone else 0),
            website_points=(self.WEBSITE_POINTS if valid_website else 0),
            address_points=(
                self.ADDRESS_POINTS if self._has_text(business.address) else 0
            ),
            category_points=(
                self.CATEGORY_POINTS if self._has_text(business.category) else 0
            ),
            contact_bonus=(self.MULTIPLE_CONTACT_BONUS if contact_methods >= 2 else 0),
        )

    def score_business(
        self,
        business: Business,
        region: str | None = None,
    ) -> int:
        """Calculate a business score without modifying it."""
        result = self.score_with_breakdown(
            business,
            region=region,
        )

        return result.total_score

    @staticmethod
    def get_quality(score: int) -> LeadQuality:
        """Classify a validated numeric score."""
        return classify_lead_score(score)

    def evaluate_business(
        self,
        business: Business,
        region: str | None = None,
    ) -> int:
        """Calculate and store the current business score."""
        business.lead_score = self.score_business(
            business,
            region=region,
        )

        return business.lead_score

    def evaluate_businesses(
        self,
        businesses: list[Business],
        region: str | None = None,
    ) -> list[Business]:
        """Evaluate and store scores for multiple businesses."""
        normalized_region = normalize_country_code(region)

        for business in businesses:
            self.evaluate_business(
                business,
                region=normalized_region,
            )

        return businesses
