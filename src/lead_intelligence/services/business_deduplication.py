
import re
from urllib.parse import urlparse

from src.lead_intelligence.models.business import Business


class BusinessDeduplicationService:

    @staticmethod
    def normalize_domain(website: str | None) -> str | None:
        if not website:
            return None

        try:
            parsed = urlparse(website.strip())

            if parsed.scheme.lower() not in {"http", "https"}:
                return None

            hostname = parsed.hostname

            if not hostname:
                return None

            return hostname.lower().removeprefix("www.")

        except ValueError:
            return None

    @staticmethod
    def normalize_phone(phone: str) -> str:
        return re.sub(r"\D", "", phone or "")

    @staticmethod
    def normalize_text(value: str | None) -> str:
        if not value:
            return ""

        return " ".join(value.lower().split())

    def are_duplicates(
        self,
        first: Business,
        second: Business,
    ) -> bool:

        first_domain = self.normalize_domain(first.website)
        second_domain = self.normalize_domain(second.website)

        # Conflicting website domains indicate different identities.
        if (
            first_domain
            and second_domain
            and first_domain != second_domain
        ):
            return False

        # Matching website domains are the strongest signal.
        if first_domain and first_domain == second_domain:
            return True

        first_phones = {
            normalized
            for phone in first.phone_numbers
                if (normalized := self.normalize_phone(phone))
                }

        second_phones = {
            normalized
            for phone in second.phone_numbers
                if (normalized := self.normalize_phone(phone))
        }

        if first_phones.intersection(second_phones):
            return True

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
    def merge_business(
        existing: Business,
        incoming: Business,
    ) -> Business:

        existing.emails = list(
            dict.fromkeys(existing.emails + incoming.emails)
        )

        existing.phone_numbers = list(
            dict.fromkeys(
                existing.phone_numbers + incoming.phone_numbers
            )
        )

        if not existing.website:
            existing.website = incoming.website

        if not existing.address:
            existing.address = incoming.address

        if not existing.category:
            existing.category = incoming.category

        return existing

    def deduplicate(
        self,
        businesses: list[Business],
    ) -> list[Business]:

        unique_businesses = []

        for incoming in businesses:
            duplicate = None

            for existing in unique_businesses:
                if self.are_duplicates(existing, incoming):
                    duplicate = existing
                    break

            if duplicate:
                self.merge_business(duplicate, incoming)
            else:
                unique_businesses.append(incoming)

        return unique_businesses
