from enum import StrEnum


class ExtractionStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    NO_WEBSITE = "no_website"
    NO_CONTACTS = "no_contacts"
