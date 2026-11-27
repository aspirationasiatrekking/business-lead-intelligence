from datetime import datetime

from src.lead_intelligence.database.models import (
    BusinessContactRecord,
    BusinessRecord,
    ContactSourceRecord,
)
from src.lead_intelligence.database.repositories.observations import (
    touch_observation,
    validate_observation_time,
)


class ContactRepository:
    """Append-only persistence operations for business contacts."""

    @staticmethod
    def _identity(
        contact: BusinessContactRecord,
    ) -> tuple[str, str]:
        return (
            contact.contact_type,
            contact.normalized_value,
        )

    @staticmethod
    def _merge_contact_sources(
        existing: BusinessContactRecord,
        incoming: BusinessContactRecord,
        observed_at: datetime,
    ) -> None:
        """Append new contact evidence and refresh known sources."""

        existing_sources = {source.source_url: source for source in existing.sources}

        for incoming_source in incoming.sources:
            source = existing_sources.get(
                incoming_source.source_url,
            )

            if source is None:
                source = ContactSourceRecord(
                    source_url=incoming_source.source_url,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                )

                existing.sources.append(source)

                existing_sources[source.source_url] = source

            else:
                touch_observation(
                    source,
                    observed_at,
                )

    def merge(
        self,
        existing: BusinessRecord,
        incoming_contacts: list[BusinessContactRecord],
        *,
        observed_at: datetime,
    ) -> None:
        """Merge validated contacts into a loaded business record.

        The caller owns the transaction and identity coordination.
        """

        observed_at = validate_observation_time(observed_at)

        existing_contacts = {
            self._identity(contact): contact for contact in existing.contacts
        }

        for incoming in incoming_contacts:
            identity = self._identity(incoming)

            contact = existing_contacts.get(identity)

            if contact is None:
                contact = BusinessContactRecord(
                    contact_type=incoming.contact_type,
                    value=incoming.value,
                    normalized_value=incoming.normalized_value,
                    first_seen_at=observed_at,
                    last_seen_at=observed_at,
                    sources=[],
                )

                existing.contacts.append(contact)

                existing_contacts[identity] = contact

            else:
                touch_observation(
                    contact,
                    observed_at,
                )

            self._merge_contact_sources(
                contact,
                incoming,
                observed_at,
            )
