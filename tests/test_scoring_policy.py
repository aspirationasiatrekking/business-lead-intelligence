import pytest

from src.lead_intelligence.exporters.export_schema import serialize_business
from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.extraction_status import ExtractionStatus
from src.lead_intelligence.models.scoring_policy import SCORING_VERSION
from src.lead_intelligence.services.lead_scoring import LeadScoringService


@pytest.mark.parametrize("value", ["Unknown", "N/A", "---", "None", "  ", "TBD"])
def test_placeholders_do_not_earn_points(value):
    business = Business(name="Agency", address=value, category=value)
    assert LeadScoringService().score_business(business) == 0


def test_third_party_website_does_not_earn_points():
    business = Business(
        name="Agency",
        website="https://facebook.com/agency",
        emails=["info@example.com"],
    )
    result = LeadScoringService().score_with_breakdown(business)
    assert result.total_score == 30
    assert result.website_points == result.contact_bonus == 0
    assert "Website rejected by business website policy" in result.warnings


def test_reliability_is_separate_from_completeness():
    business = Business(
        name="Agency",
        website="https://example.com",
        emails=["INFO@example.com", "info@example.com", "sales@example.com"],
        phone_numbers=["+12025550123"],
        email_sources={
            "info@example.com": ["https://www.example.com/contact"],
            "sales@example.com": ["https://other.com/contact"],
        },
        phone_sources={"+12025550123": ["https://example.com/contact"]},
        geographic_conflicts=["Country conflict"],
        extraction_status=ExtractionStatus.PARTIAL,
    )
    result = LeadScoringService().score_with_breakdown(business)
    assert result.total_score == 80
    assert result.sourced_email_count == result.sourced_phone_count == 1
    assert "Unresolved geographic conflicts" in result.warnings
    assert "Extraction status: partial" in result.warnings
    assert "Some valid emails lack same-site source evidence" in result.warnings
    assert result.policy_version == SCORING_VERSION
    assert business.lead_score is None


def test_stale_score_is_recomputed_without_mutating_export_input():
    service = LeadScoringService()
    business = Business(name="Agency", emails=["info@example.com"])
    service.evaluate_business(business)
    assert service.is_score_current(business)
    business.emails.clear()
    assert not service.is_score_current(business)
    assert serialize_business(business, service)[-2:] == [0, "Low"]
    assert business.lead_score == 30


def test_version_and_region_changes_invalidate_cached_score():
    service = LeadScoringService()
    business = Business(name="Agency", phone_numbers=["2025550123"])
    service.evaluate_business(business, region="US")
    assert service.is_score_current(business, region="us")
    assert not service.is_score_current(business, region="NP")
    business.score_version = "old"
    assert not service.is_score_current(business, region="US")
    business.invalidate_score()
    assert business.score_version is None
    assert business.lead_score is None


def test_legacy_explicit_scores_remain_authoritative():
    business = Business(name="Agency", lead_score=85)
    assert serialize_business(business, LeadScoringService())[-2:] == [85, "High"]
