from email_validator import EmailNotValidError, validate_email

from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)
from src.lead_intelligence.models import scoring_policy
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.lead_quality import (
    LeadQuality,
    classify_lead_score,
)
from src.lead_intelligence.models.scoring_result import ScoringResult
from src.lead_intelligence.utils.country_utils import normalize_country_code
from src.lead_intelligence.utils.website_policy import (
    is_candidate_business_website,
    same_website,
)


class LeadScoringService:
    MAX_SCORE = scoring_policy.MAX_SCORE

    EMAIL_POINTS = scoring_policy.EMAIL_POINTS
    PHONE_POINTS = scoring_policy.PHONE_POINTS
    WEBSITE_POINTS = scoring_policy.WEBSITE_POINTS
    ADDRESS_POINTS = scoring_policy.ADDRESS_POINTS
    CATEGORY_POINTS = scoring_policy.CATEGORY_POINTS
    MULTIPLE_CONTACT_BONUS = scoring_policy.MULTIPLE_CONTACT_BONUS

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

        return is_candidate_business_website(website)

    @staticmethod
    def _has_text(value: str | None) -> bool:
        """Check whether a field contains meaningful text."""
        if not isinstance(value, str):
            return False
        key = " ".join(value.casefold().split())
        placeholders = {
            "unknown",
            "n/a",
            "na",
            "none",
            "null",
            "not available",
            "not specified",
            "-",
            "--",
            "tbd",
        }
        return key not in placeholders and any(char.isalnum() for char in key)

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

    @staticmethod
    def _snapshot(business: Business, region: str | None) -> tuple:
        return (
            tuple(business.emails),
            tuple(business.phone_numbers),
            business.website,
            business.address,
            business.category,
            region,
            business.lead_score,
        )

    def is_score_current(self, business: Business, region: str | None = None) -> bool:
        """Preserve legacy explicit scores; verify service-generated scores."""
        if business.lead_score is None:
            return False
        if business.score_version is None:
            return business._score_snapshot is None
        return (
            business.score_version == scoring_policy.SCORING_VERSION
            and business._score_snapshot
            == self._snapshot(business, self._resolve_region(business, region))
        )

    def _reliability(
        self, business: Business, region: str | None
    ) -> tuple[int, int, tuple[str, ...]]:
        def has_source(urls: list[str]) -> bool:
            return bool(business.website) and any(
                same_website(business.website, url) for url in urls
            )

        emails = {
            email.strip().casefold()
            for email in business.emails
            if self.has_valid_email([email])
        }
        phones = {
            number
            for phone in business.phone_numbers
            if (number := normalize_phone_number(phone, region=region))
        }
        sourced_emails = sum(
            has_source(business.email_sources.get(email, [])) for email in emails
        )
        sourced_phones = sum(
            has_source(business.phone_sources.get(phone, [])) for phone in phones
        )
        warnings = []
        if emails and sourced_emails < len(emails):
            warnings.append("Some valid emails lack same-site source evidence")
        if phones and sourced_phones < len(phones):
            warnings.append("Some valid phones lack same-site source evidence")
        if business.geographic_conflicts:
            warnings.append("Unresolved geographic conflicts")
        if business.extraction_status != ExtractionStatus.SUCCESS:
            warnings.append(f"Extraction status: {business.extraction_status.value}")
        if business.website and not self.has_valid_website(business.website):
            warnings.append("Website rejected by business website policy")
        return sourced_emails, sourced_phones, tuple(warnings)

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

        sourced_emails, sourced_phones, warnings = self._reliability(
            business, selected_region
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
            sourced_email_count=sourced_emails,
            sourced_phone_count=sourced_phones,
            warnings=warnings,
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

        business.score_version = scoring_policy.SCORING_VERSION
        business._score_snapshot = self._snapshot(
            business, self._resolve_region(business, region)
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
