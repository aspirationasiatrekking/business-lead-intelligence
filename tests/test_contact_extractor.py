from src.lead_intelligence.extractors.contact_extractor import (
    extract_emails,
    extract_phone_numbers,
    normalize_phone_number,
)


def test_extract_single_email():
    text = "Contact us at info@example.com"

    result = extract_emails(text)

    assert result == ["info@example.com"]


def test_extract_multiple_emails():
    text = """
    info@example.com
    sales@company.org
    support@business.net
    """

    result = extract_emails(text)

    assert len(result) == 3
    assert "info@example.com" in result
    assert "sales@company.org" in result
    assert "support@business.net" in result


def test_remove_duplicate_emails():
    text = """
    info@example.com
    info@example.com
    sales@company.org
    """

    result = extract_emails(text)

    assert len(result) == 2


def test_normalize_email_case():
    text = "INFO@EXAMPLE.COM"

    result = extract_emails(text)

    assert result == ["info@example.com"]


def test_no_emails():
    text = "Welcome to our trekking company website."

    result = extract_emails(text)

    assert result == []


def test_extract_nepal_phone_number():
    text = "Contact us at 9812345678"

    result = extract_phone_numbers(text, region="NP")

    assert "+9779812345678" in result


def test_extract_international_phone_number():
    text = "Call us at +1 202-555-0145"

    result = extract_phone_numbers(text)

    assert "+12025550145" in result


def test_ignore_invalid_phone_number():
    text = "Call us at 12345"

    result = extract_phone_numbers(text, region="NP")

    assert result == []


def test_remove_duplicate_phone_numbers():
    text = """
    +977 9812345678
    +9779812345678
    """

    result = extract_phone_numbers(text)

    assert result.count("+9779812345678") == 1


def test_no_phone_numbers():
    text = "Welcome to our trekking company website."

    result = extract_phone_numbers(text)

    assert result == []


def test_normalize_nepal_local_number():
    result = normalize_phone_number("984-6041887", region="NP")
    assert result == "+9779846041887"


def test_normalize_nepal_international_number():
    result = normalize_phone_number("+9779846041887", region="NP")
    assert result == "+9779846041887"


def test_normalize_foreign_number():
    result = normalize_phone_number("+61406927726", region="NP")
    assert result == "+61406927726"


def test_normalize_invalid_number():
    result = normalize_phone_number("12345", region="NP")
    assert result is None


def test_normalize_invalid_input():
    result = normalize_phone_number("not a phone number", region="NP")
    assert result is None


def test_reject_invalid_email_addresses():
    text = """
    info@example.com
    invalid-email
    user@
    @example.com
    user@.com
    """

    result = extract_emails(text)

    assert result == ["info@example.com"]


def test_preserve_email_discovery_order():
    text = """
    info@example.com
    sales@example.com
    support@example.com
    """

    result = extract_emails(text)

    assert result == [
        "info@example.com",
        "sales@example.com",
        "support@example.com",
    ]


def test_remove_duplicate_emails_case_insensitively():
    text = """
    INFO@example.com
    info@example.com
    Info@Example.com
    """

    result = extract_emails(text)

    assert result == ["info@example.com"]
