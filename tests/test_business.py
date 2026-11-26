import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.lead_quality import LeadQuality

# Basic business model tests


def test_create_business():
    business = Business(
        name="Nepal Hiking Team",
        address="Thamel, Kathmandu, Nepal",
        phone_numbers=["+977123456789"],
        website="https://www.nepalhikingteam.com/",
    )

    assert business.name == "Nepal Hiking Team"
    assert business.address == "Thamel, Kathmandu, Nepal"
    assert business.phone_numbers == ["+977123456789"]
    assert business.website == "https://www.nepalhikingteam.com/"


# Geographic information tests


def test_business_with_geographic_information():
    business = Business(
        name="Example Trekking Company",
        city="Kathmandu",
        district="Kathmandu",
        state="Bagmati",
        country="Nepal",
        country_code="NP",
    )

    assert business.city == "Kathmandu"
    assert business.district == "Kathmandu"
    assert business.state == "Bagmati"
    assert business.country == "Nepal"
    assert business.country_code == "NP"


def test_business_geographic_fields_default_to_none():
    business = Business(name="Example Business")

    assert business.city is None
    assert business.district is None
    assert business.state is None
    assert business.country is None
    assert business.country_code is None


def test_business_contact_lists_are_independent():
    first = Business(name="First Business")
    second = Business(name="Second Business")

    first.emails.append("info@example.com")
    first.phone_numbers.append("+9779846041887")

    assert second.emails == []
    assert second.phone_numbers == []


def test_business_with_international_location():
    business = Business(
        name="Example Travel Agency",
        city="London",
        country="United Kingdom",
        country_code="GB",
    )

    assert business.city == "London"
    assert business.country == "United Kingdom"
    assert business.country_code == "GB"
    assert business.district is None
    assert business.state is None


# Source tracking tests


def test_business_with_source_urls():
    business = Business(
        name="Example Business",
        source_urls=[
            "https://example.com",
            "https://example.com/contact",
        ],
    )

    assert business.source_urls == [
        "https://example.com",
        "https://example.com/contact",
    ]


def test_business_with_contact_page_urls():
    business = Business(
        name="Example Business",
        contact_page_urls=[
            "https://example.com/contact",
            "https://example.com/about",
        ],
    )

    assert business.contact_page_urls == [
        "https://example.com/contact",
        "https://example.com/about",
    ]


def test_business_source_fields_default_to_empty_lists():
    business = Business(name="Example Business")

    assert business.source_urls == []
    assert business.contact_page_urls == []


def test_business_source_lists_are_independent():
    first = Business(name="First Business")
    second = Business(name="Second Business")

    first.source_urls.append("https://example.com")
    first.contact_page_urls.append("https://example.com/contact")

    assert second.source_urls == []
    assert second.contact_page_urls == []


# Extraction status tests


def test_business_extraction_status_defaults_to_pending():
    business = Business(name="Example Business")

    assert business.extraction_status is ExtractionStatus.PENDING


def test_business_with_explicit_extraction_status():
    business = Business(
        name="Example Business",
        extraction_status=ExtractionStatus.SUCCESS,
    )

    assert business.extraction_status is ExtractionStatus.SUCCESS


def test_business_extraction_status_can_be_updated():
    business = Business(name="Example Business")

    business.extraction_status = ExtractionStatus.PARTIAL

    assert business.extraction_status is ExtractionStatus.PARTIAL


# Lead scoring and quality tests


def test_business_lead_score_defaults_to_none():
    business = Business(name="Example Business")

    assert business.lead_score is None
    assert business.lead_quality is None


def test_business_with_zero_lead_score():
    business = Business(
        name="Example Business",
        lead_score=0,
    )

    assert business.lead_score == 0
    assert business.lead_quality is LeadQuality.LOW


def test_business_with_high_lead_score():
    business = Business(
        name="Example Business",
        lead_score=90,
    )

    assert business.lead_quality is LeadQuality.HIGH


def test_business_lead_quality_reflects_score_changes():
    business = Business(
        name="Example Business",
        lead_score=90,
    )

    assert business.lead_quality is LeadQuality.HIGH

    business.lead_score = 60

    assert business.lead_quality is LeadQuality.MEDIUM

    business.lead_score = 20

    assert business.lead_quality is LeadQuality.LOW


# Business name validation tests


@pytest.mark.parametrize("name", ["", " ", "\t"])
def test_business_rejects_empty_names(name):
    with pytest.raises(ValueError):
        Business(name=name)


@pytest.mark.parametrize("name", [None, 123, True])
def test_business_rejects_invalid_name_types(name):
    with pytest.raises(TypeError):
        Business(name=name)


# Text field validation tests


def test_business_normalizes_text_fields():
    business = Business(
        name="  Example Company  ",
        address="  Kathmandu  ",
        category="  Travel agency  ",
        website=" ",
    )

    assert business.name == "Example Company"
    assert business.address == "Kathmandu"
    assert business.category == "Travel agency"
    assert business.website is None


def test_business_rejects_invalid_optional_text():
    with pytest.raises(TypeError):
        Business(
            name="Example Company",
            address=123,
        )


# Country code validation tests


def test_business_normalizes_country_code():
    business = Business(
        name="Example Company",
        country_code=" np ",
    )

    assert business.country_code == "NP"


@pytest.mark.parametrize(
    "country_code",
    ["N", "NPL", "12", "N1", "日本"],
)
def test_business_rejects_invalid_country_code(country_code):
    with pytest.raises(ValueError):
        Business(
            name="Example Company",
            country_code=country_code,
        )


# Collection validation tests


@pytest.mark.parametrize(
    "field_name",
    [
        "emails",
        "phone_numbers",
        "source_urls",
        "contact_page_urls",
    ],
)
def test_business_rejects_non_list_values(field_name):
    with pytest.raises(TypeError):
        Business(
            name="Example Company",
            **{field_name: "invalid"},
        )


@pytest.mark.parametrize(
    "field_name",
    [
        "emails",
        "phone_numbers",
        "source_urls",
        "contact_page_urls",
    ],
)
def test_business_rejects_non_string_list_items(field_name):
    with pytest.raises(TypeError):
        Business(
            name="Example Company",
            **{field_name: [123]},
        )


def test_business_copies_supplied_lists():
    emails = ["info@example.com"]

    business = Business(
        name="Example Company",
        emails=emails,
    )

    emails.append("sales@example.com")

    assert business.emails == ["info@example.com"]


# Extraction status validation tests


def test_business_normalizes_extraction_status():
    business = Business(
        name="Example Company",
        extraction_status="success",
    )

    assert business.extraction_status is ExtractionStatus.SUCCESS


def test_business_rejects_invalid_extraction_status():
    with pytest.raises(ValueError):
        Business(
            name="Example Company",
            extraction_status="unknown",
        )


# Lead score validation tests


@pytest.mark.parametrize(
    "score",
    [-1, 101, True, False, 50.5, "80"],
)
def test_business_rejects_invalid_initial_scores(score):
    with pytest.raises(ValueError):
        Business(
            name="Example Company",
            lead_score=score,
        )


def test_business_lead_quality_rejects_invalid_updated_score():
    business = Business(name="Example Company")

    business.lead_score = 101

    with pytest.raises(ValueError):
        _ = business.lead_quality
