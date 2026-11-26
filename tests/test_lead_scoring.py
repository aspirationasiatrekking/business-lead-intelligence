import pytest

from src.lead_intelligence.models.business import Business
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
