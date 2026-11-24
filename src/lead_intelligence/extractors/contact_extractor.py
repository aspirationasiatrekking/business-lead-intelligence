
import re





import phonenumbers


def normalize_phone_number(
    phone: str,
    region: str | None = None
) -> str | None:
    try:
        parsed_number = phonenumbers.parse(phone, region)

        if not phonenumbers.is_valid_number(parsed_number):
            return None

        return phonenumbers.format_number(
            parsed_number,
            phonenumbers.PhoneNumberFormat.E164
        )

    except phonenumbers.NumberParseException:
        return None




def extract_phone_numbers(
    text: str,
    region: str | None = None
) -> list[str]:
    phone_numbers = []

    for match in phonenumbers.PhoneNumberMatcher(text, region):
        formatted_number = normalize_phone_number(
            match.raw_string,
            region=region
        )

        if formatted_number and formatted_number not in phone_numbers:
            phone_numbers.append(formatted_number)

    return phone_numbers



def extract_emails(text: str) -> list[str]:
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"

    emails = re.findall(pattern, text)

    # Remove duplicates and normalize case
    unique_emails = list({
        email.lower()
        for email in emails
    })

    return unique_emails
