import re
from urllib.parse import unquote

import phonenumbers
from bs4 import BeautifulSoup
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

    # Match whole candidate tokens rather than fragments of invalid addresses.
    pattern = r"[\w.!#$%&'*+/=?^`{|}~@-]+@[\w.@-]+"

    candidates = re.findall(pattern, text)

    unique_emails = []

    for candidate in candidates:
        candidate = candidate.rstrip(".")
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


def extract_html_contacts(
    html: str,
    region: str | None = None,
) -> tuple[list[str], list[str]]:
    """Extract visible text and explicit contact URI targets without fetching links."""
    if not isinstance(html, str) or not html:
        return [], []

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "template"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    emails = extract_emails(text)
    phones = extract_phone_numbers(text, region=region)

    for link in soup.find_all("a", href=True):
        href = link.get("href")
        if not isinstance(href, str):
            continue
        scheme, separator, target = href.strip().partition(":")
        if not separator or scheme.lower() not in {"mailto", "tel"}:
            continue
        # Ignore mail subject/body and telephone URI parameters.
        target = unquote(target.split("?", 1)[0])
        if scheme.lower() == "mailto":
            for recipient in target.split(","):
                try:
                    email = validate_email(
                        recipient.strip(), check_deliverability=False
                    ).normalized.lower()
                except EmailNotValidError:
                    continue
                emails.append(email)
        else:
            number = normalize_phone_number(target.split(";", 1)[0], region=region)
            if number:
                phones.append(number)

    return list(dict.fromkeys(emails)), list(dict.fromkeys(phones))
