from urllib.parse import urlparse

from src.lead_intelligence.extractors.contact_extractor import (
    normalize_phone_number,
)
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.utils.business_identity import normalize_serper_cid
from src.lead_intelligence.utils.url_utils import normalize_website_url
from src.lead_intelligence.utils.website_policy import is_candidate_business_website


class BusinessDeduplicationService:
    GEOGRAPHIC_FIELDS = (
        "city",
        "district",
        "state",
        "country",
        "country_code",
    )

    MERGEABLE_TEXT_FIELDS = (
        "address",
        "category",
        "city",
        "district",
        "state",
        "country",
        "country_code",
    )

    @staticmethod
    def normalize_domain(website: str | None) -> str | None:
        """Return a normalized domain from a valid website."""
        if not is_candidate_business_website(website):
            return None

        normalized_url = normalize_website_url(website)

        if normalized_url is None:
            return None

        hostname = urlparse(normalized_url).hostname

        if hostname is None:
            return None

        return hostname.lower().removeprefix("www.")

    @staticmethod
    def normalize_phone(
        phone: str,
        region: str | None = None,
    ) -> str:
        """Return a validated international phone matching key."""
        return (
            normalize_phone_number(
                phone,
                region=region,
            )
            or ""
        )

    @staticmethod
    def normalize_text(value: str | None) -> str:
        """Normalize text for case-insensitive comparisons."""
        if not isinstance(value, str):
            return ""

        return " ".join(value.casefold().split())

    def _has_geographic_conflict(
        self,
        first: Business,
        second: Business,
    ) -> bool:
        """Check whether known geographic values contradict each other."""
        for field_name in self.GEOGRAPHIC_FIELDS:
            first_value = self.normalize_text(getattr(first, field_name))

            second_value = self.normalize_text(getattr(second, field_name))

            if first_value and second_value and first_value != second_value:
                return True

        return False

    def _has_address_conflict(
        self,
        first: Business,
        second: Business,
    ) -> bool:
        """Reject conflicting known addresses."""
        first_address = self.normalize_text(first.address)
        second_address = self.normalize_text(second.address)

        return bool(
            first_address and second_address and first_address != second_address
        )

    def _get_phone_keys(
        self,
        business: Business,
    ) -> set[str]:
        """Build validated phone matching keys."""
        return {
            normalized
            for phone in business.phone_numbers
            if (
                normalized := self.normalize_phone(
                    phone,
                    region=business.country_code,
                )
            )
        }

    def are_duplicates(
        self,
        first: Business,
        second: Business,
    ) -> bool:
        """Determine whether two records represent the same business."""

        # Conflicting geographic information takes precedence.
        if self._has_geographic_conflict(first, second):
            return False

        if self._has_address_conflict(first, second):
            return False

        first_cid = normalize_serper_cid(first.serper_cid)
        second_cid = normalize_serper_cid(second.serper_cid)
        if first_cid and second_cid:
            return first_cid == second_cid

        first_domain = self.normalize_domain(first.website)
        second_domain = self.normalize_domain(second.website)

        # Different known domains indicate different identities.
        if first_domain and second_domain and first_domain != second_domain:
            return False

        # Matching domains without known location conflicts.
        if first_domain and first_domain == second_domain:
            return True

        # Match only validated phone numbers.
        first_phones = self._get_phone_keys(first)
        second_phones = self._get_phone_keys(second)

        if first_phones.intersection(second_phones):
            return True

        # Fall back to matching normalized name and address.
        first_name = self.normalize_text(first.name)
        second_name = self.normalize_text(second.name)

        first_address = self.normalize_text(first.address)
        second_address = self.normalize_text(second.address)

        return (
            bool(first_name)
            and first_name == second_name
            and bool(first_address)
            and first_address == second_address
        )

    @staticmethod
    def _merge_unique_values(
        existing: list[str],
        incoming: list[str],
    ) -> list[str]:
        """Merge unique values while preserving their original order."""
        return list(dict.fromkeys(existing + incoming))

    @staticmethod
    def _merge_emails(
        existing: list[str],
        incoming: list[str],
    ) -> list[str]:
        """Merge email addresses case-insensitively."""
        merged = {}

        for email in existing + incoming:
            value = email.strip()

            if value:
                merged.setdefault(
                    value.lower(),
                    value,
                )

        return list(merged.values())

    def _merge_phone_numbers(
        self,
        existing: Business,
        incoming: Business,
    ) -> list[str]:
        """Normalize valid numbers without silently losing other values."""
        merged = []

        records = (
            (
                existing.phone_numbers,
                existing.country_code,
            ),
            (
                incoming.phone_numbers,
                incoming.country_code,
            ),
        )

        for phone_numbers, region in records:
            for phone in phone_numbers:
                normalized = self.normalize_phone(
                    phone,
                    region=region,
                )

                # Preserve unrecognized values for later validation.
                value = normalized or phone.strip()

                if value and value not in merged:
                    merged.append(value)

        return merged

    @staticmethod
    def _merge_extraction_status(
        existing: ExtractionStatus,
        incoming: ExtractionStatus,
    ) -> ExtractionStatus:
        """Combine extraction outcomes conservatively."""
        if existing == incoming:
            return existing

        if existing == ExtractionStatus.PENDING:
            return incoming

        if incoming == ExtractionStatus.PENDING:
            return existing

        if existing == ExtractionStatus.NO_WEBSITE:
            return incoming

        if incoming == ExtractionStatus.NO_WEBSITE:
            return existing

        return ExtractionStatus.PARTIAL

    @staticmethod
    def _scoring_inputs(business: Business) -> tuple:
        """Capture fields that can affect the lead score."""
        return (
            tuple(business.emails),
            tuple(business.phone_numbers),
            business.website,
            business.address,
            business.category,
            business.country_code,
        )

    def merge_business(
        self,
        existing: Business,
        incoming: Business,
    ) -> Business:
        """Merge duplicate records into the existing business."""

        if not self.are_duplicates(existing, incoming):
            raise ValueError(
                "Cannot merge businesses with conflicting or "
                "insufficient identity information."
            )

        original_scoring_inputs = self._scoring_inputs(existing)

        existing.emails = self._merge_emails(
            existing.emails,
            incoming.emails,
        )

        existing.phone_numbers = self._merge_phone_numbers(
            existing,
            incoming,
        )

        existing_domain = self.normalize_domain(existing.website)
        incoming_domain = self.normalize_domain(incoming.website)

        # Replace missing or invalid websites with valid websites.
        if not existing_domain and incoming_domain:
            existing.website = incoming.website

        # Fill missing scalar values without overwriting known data.
        for field_name in self.MERGEABLE_TEXT_FIELDS:
            existing_value = getattr(existing, field_name)
            incoming_value = getattr(incoming, field_name)

            if not existing_value and incoming_value:
                setattr(
                    existing,
                    field_name,
                    incoming_value,
                )

        if existing.serper_cid is None:
            existing.serper_cid = incoming.serper_cid

        # Keep coordinate pairs together; never combine unrelated axes.
        if (
            existing.latitude is None
            and existing.longitude is None
            and incoming.latitude is not None
            and incoming.longitude is not None
        ):
            existing.latitude = incoming.latitude
            existing.longitude = incoming.longitude

        existing.source_urls = self._merge_unique_values(
            existing.source_urls,
            incoming.source_urls,
        )

        existing.contact_page_urls = self._merge_unique_values(
            existing.contact_page_urls,
            incoming.contact_page_urls,
        )

        for field_name in ("email_sources", "phone_sources"):
            target = getattr(existing, field_name)
            for key, urls in getattr(incoming, field_name).items():
                target[key] = self._merge_unique_values(target.get(key, []), urls)

        for key, sources in incoming.geographic_sources.items():
            if getattr(existing, key, None) == getattr(incoming, key, None):
                existing.geographic_sources[key] = self._merge_unique_values(
                    existing.geographic_sources.get(key, []), sources
                )
        existing.geographic_conflicts = self._merge_unique_values(
            existing.geographic_conflicts, incoming.geographic_conflicts
        )

        existing.extraction_status = self._merge_extraction_status(
            existing.extraction_status,
            incoming.extraction_status,
        )

        # A score calculated before enrichment may no longer be valid.
        if self._scoring_inputs(existing) != original_scoring_inputs:
            existing.lead_score = None

        return existing

    def deduplicate(
        self,
        businesses: list[Business],
    ) -> list[Business]:
        """Remove unambiguous duplicates while preserving input order."""
        unique_businesses = []

        for incoming in businesses:
            matches = [
                existing
                for existing in unique_businesses
                if self.are_duplicates(existing, incoming)
            ]

            cid = normalize_serper_cid(incoming.serper_cid)
            exact_matches = [
                existing
                for existing in matches
                if cid and normalize_serper_cid(existing.serper_cid) == cid
            ]
            if exact_matches:
                matches = exact_matches

            if len(matches) == 1:
                self.merge_business(
                    matches[0],
                    incoming,
                )

            else:
                # Zero matches: new business.
                # Multiple matches: ambiguous identity, keep separate.
                unique_businesses.append(incoming)

        return unique_businesses
