
import re

import phonenumbers
from email_validator import EmailNotValidError, validate_email


def normalize_phone_number(
    phone: str,
    region: str | None = None,
) -> str | None:
    if not isinstance(phone, str) or not phone.strip():
        return None

    try:
        parsed_number = phonenumbers.parse(phone, region)

        if not phonenumbers.is_valid_number(parsed_number):
            return None

        return phonenumbers.format_number(
            parsed_number,
            phonenumbers.PhoneNumberFormat.E164,
        )

    except phonenumbers.NumberParseException:
        return None


def extract_phone_numbers(
    text: str,
    region: str | None = None,
) -> list[str]:
    if not isinstance(text, str) or not text:
        return []

    phone_numbers = []

    for match in phonenumbers.PhoneNumberMatcher(text, region):
        formatted_number = normalize_phone_number(
            match.raw_string,
            region=region,
        )

        if formatted_number and formatted_number not in phone_numbers:
            phone_numbers.append(formatted_number)

    return phone_numbers


def extract_emails(text: str) -> list[str]:
    if not isinstance(text, str) or not text:
        return []

    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    candidates = re.findall(pattern, text)

    unique_emails = []

    for candidate in candidates:
        try:
            validated = validate_email(
                candidate,
                check_deliverability=False,
            )

            email = validated.normalized.lower()

            if email not in unique_emails:
                unique_emails.append(email)

        except EmailNotValidError:
            continue

    return unique_emails
