from dataclasses import FrozenInstanceError

import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.scoring_result import ScoringResult
from src.lead_intelligence.services.lead_scoring import LeadScoringService


def test_score_complete_business():
    service = LeadScoringService()

    business = Business(
        name="Nepal Hiking Team",
        address="Thamel, Kathmandu",
        emails=["sales@example.com"],
        phone_numbers=["+97714989212"],
        website="https://example.com",
        category="Travel agency",
    )

    assert service.score_business(business) == 100


def test_score_business_without_contacts():
    service = LeadScoringService()

    business = Business(name="Example Company")

    assert service.score_business(business) == 0


def test_score_business_with_email_only():
    service = LeadScoringService()

    business = Business(
        name="Example Company",
        emails=["info@example.com"],
    )

    assert service.score_business(business) == 30


def test_score_business_with_multiple_contact_methods():
    service = LeadScoringService()

    business = Business(
        name="Example Company",
        emails=["info@example.com"],
        phone_numbers=["+97714989212"],
    )

    assert service.score_business(business) == 65


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (100, "High"),
        (80, "High"),
        (79, "Medium"),
        (50, "Medium"),
        (49, "Low"),
        (0, "Low"),
    ],
)
def test_get_quality(score, expected):
    service = LeadScoringService()

    assert service.get_quality(score) == expected


@pytest.mark.parametrize("score", [-1, 101])
def test_get_quality_rejects_invalid_scores(score):
    service = LeadScoringService()

    with pytest.raises(ValueError):
        service.get_quality(score)


def test_score_business_does_not_modify_business():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        emails=["info@example.com"],
    )

    assert service.score_business(business) == 30
    assert business.lead_score is None


def test_evaluate_business_stores_lead_score():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        emails=["info@example.com"],
    )

    score = service.evaluate_business(business)

    assert score == 30
    assert business.lead_score == 30
    assert business.lead_quality == "Low"


def test_evaluate_business_recalculates_existing_score():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        lead_score=100,
    )

    score = service.evaluate_business(business)

    assert score == 0
    assert business.lead_score == 0
    assert business.lead_quality == "Low"


@pytest.mark.parametrize(
    "score",
    [True, False, 50.5, "80", None],
)
def test_get_quality_rejects_invalid_score_types(score):
    service = LeadScoringService()

    with pytest.raises(ValueError):
        service.get_quality(score)


# Detailed scoring tests


def test_scoring_result_defaults():
    result = ScoringResult()

    assert result.total_score == 0
    assert result.quality == "Low"


def test_scoring_result_calculates_total():
    result = ScoringResult(
        email_points=30,
        phone_points=20,
        website_points=15,
        address_points=10,
        category_points=10,
        contact_bonus=15,
    )

    assert result.total_score == 100
    assert result.quality == "High"


def test_scoring_result_caps_maximum_score():
    result = ScoringResult(
        email_points=100,
        phone_points=50,
    )

    assert result.total_score == 100


def test_scoring_result_is_immutable():
    result = ScoringResult(
        email_points=30,
    )

    with pytest.raises(FrozenInstanceError):
        result.email_points = 50


@pytest.mark.parametrize(
    "value",
    [-1, True, False, 10.5, "30", None],
)
def test_scoring_result_rejects_invalid_components(
    value,
):
    with pytest.raises(
        ValueError,
        match="Score components",
    ):
        ScoringResult(email_points=value)


def test_complete_business_scoring_breakdown():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        address="Kathmandu, Nepal",
        category="Travel agency",
        website="https://example.com",
        emails=["info@example.com"],
        phone_numbers=["+9779846041887"],
    )

    result = service.score_with_breakdown(business)

    assert result.email_points == 30
    assert result.phone_points == 20
    assert result.website_points == 15
    assert result.address_points == 10
    assert result.category_points == 10
    assert result.contact_bonus == 15

    assert result.total_score == 100
    assert result.quality == "High"


def test_scoring_breakdown_does_not_mutate_business():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        emails=["info@example.com"],
        lead_score=90,
    )

    result = service.score_with_breakdown(business)

    assert result.total_score == 30
    assert business.lead_score == 90


@pytest.mark.parametrize(
    ("emails", "expected"),
    [
        ([], False),
        (["invalid"], False),
        (["info@"], False),
        (["info@example"], False),
        (["Contact info@example.com"], False),
        (["info@example.com other text"], False),
        (["info@example.com"], True),
        ([" info@example.com "], True),
        (["invalid", "sales@example.com"], True),
    ],
)
def test_validates_complete_email_values(
    emails,
    expected,
):
    service = LeadScoringService()

    assert service.has_valid_email(emails) is expected


@pytest.mark.parametrize(
    "website",
    [
        None,
        "",
        "invalid-url",
        "ftp://example.com",
        "https://[invalid",
        "https://user@example.com",
        "https://google.com/goto?url=example",
    ],
)
def test_invalid_website_receives_no_points(website):
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        website=website,
    )

    result = service.score_with_breakdown(business)

    assert result.website_points == 0
    assert result.total_score == 0


def test_invalid_phone_receives_no_points():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        phone_numbers=["123", "invalid"],
    )

    result = service.score_with_breakdown(business)

    assert result.phone_points == 0


@pytest.mark.parametrize(
    "region",
    ["NP", "np", " Np "],
)
def test_scoring_normalizes_phone_region(region):
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        phone_numbers=["9846041887"],
    )

    result = service.score_with_breakdown(
        business,
        region=region,
    )

    assert result.phone_points == 20


def test_scoring_uses_known_business_country():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        country_code="NP",
        phone_numbers=["9846041887"],
    )

    result = service.score_with_breakdown(business)

    assert result.phone_points == 20


def test_known_country_takes_precedence_over_search_region():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        country_code="NP",
        phone_numbers=["9846041887"],
    )

    result = service.score_with_breakdown(
        business,
        region="US",
    )

    assert result.phone_points == 20


def test_international_phone_without_region():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        phone_numbers=["+12025550123"],
    )

    result = service.score_with_breakdown(business)

    assert result.phone_points == 20


def test_scoring_rejects_invalid_region():
    service = LeadScoringService()

    business = Business(name="Example Business")

    with pytest.raises(ValueError):
        service.score_business(
            business,
            region="NPL",
        )


def test_duplicate_emails_do_not_increase_score():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        emails=[
            "info@example.com",
            "sales@example.com",
            "info@example.com",
        ],
    )

    result = service.score_with_breakdown(business)

    assert result.email_points == 30
    assert result.contact_bonus == 0
    assert result.total_score == 30


def test_multiple_phones_do_not_trigger_contact_bonus():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        phone_numbers=[
            "+9779846041887",
            "+9779812345678",
        ],
    )

    result = service.score_with_breakdown(business)

    assert result.phone_points == 20
    assert result.contact_bonus == 0


@pytest.mark.parametrize(
    ("fields", "expected_score"),
    [
        (
            {
                "emails": ["info@example.com"],
                "website": "https://example.com",
            },
            60,
        ),
        (
            {
                "phone_numbers": ["+9779846041887"],
                "website": "https://example.com",
            },
            50,
        ),
        (
            {
                "emails": ["info@example.com"],
                "phone_numbers": ["+9779846041887"],
            },
            65,
        ),
    ],
)
def test_multiple_contact_method_bonus(
    fields,
    expected_score,
):
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        **fields,
    )

    result = service.score_with_breakdown(business)

    assert result.contact_bonus == 15
    assert result.total_score == expected_score


def test_address_and_category_do_not_trigger_contact_bonus():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        address="Kathmandu, Nepal",
        category="Travel agency",
    )

    result = service.score_with_breakdown(business)

    assert result.address_points == 10
    assert result.category_points == 10
    assert result.contact_bonus == 0
    assert result.total_score == 20


def test_numeric_score_matches_scoring_breakdown():
    service = LeadScoringService()

    business = Business(
        name="Example Business",
        website="https://example.com",
        emails=["info@example.com"],
    )

    assert (
        service.score_business(business)
        == service.score_with_breakdown(business).total_score
    )


def test_batch_evaluation_stores_all_scores():
    service = LeadScoringService()

    businesses = [
        Business(
            name="First Business",
            emails=["info@example.com"],
        ),
        Business(
            name="Second Business",
            phone_numbers=["+9779846041887"],
        ),
        Business(
            name="Third Business",
        ),
    ]

    result = service.evaluate_businesses(businesses)

    assert result is businesses

    assert [business.lead_score for business in result] == [30, 20, 0]


def test_batch_evaluation_handles_empty_list():
    service = LeadScoringService()

    assert service.evaluate_businesses([]) == []


def test_batch_evaluation_respects_business_regions():
    service = LeadScoringService()

    businesses = [
        Business(
            name="Nepal Business",
            country_code="NP",
            phone_numbers=["9846041887"],
        ),
        Business(
            name="US Business",
            country_code="US",
            phone_numbers=["2025550123"],
        ),
    ]

    result = service.evaluate_businesses(
        businesses,
        region="GB",
    )

    assert [business.lead_score for business in result] == [20, 20]


def test_batch_evaluation_rejects_invalid_region():
    service = LeadScoringService()

    businesses = [
        Business(name="Example Business"),
    ]

    with pytest.raises(ValueError):
        service.evaluate_businesses(
            businesses,
            region="NPL",
        )

    assert businesses[0].lead_score is None
