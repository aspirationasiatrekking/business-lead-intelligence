import pytest

from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.mapper import map_serper_place
from src.lead_intelligence.services.business_deduplication import (
    BusinessDeduplicationService,
)
from src.lead_intelligence.services.geographic_enrichment import (
    GeographicEnrichmentService,
)


@pytest.mark.parametrize(
    "address, code, state",
    [
        ("Thamel, Kathmandu, Bagmati, Nepal", "NP", "Bagmati"),
        ("Street, Toronto, Ontario, Canada", "CA", "Ontario"),
        ("Street, California, USA", "US", "California"),
        ("Street, London, UK", "GB", None),
        ("Street, Kathmandu 44600", None, None),
        ("Street, Georgia", None, None),
        ("Street, IN", None, None),
        ("Nepal", None, None),
    ],
)
def test_address_enrichment(address, code, state):
    business = Business(name="Agency", address=address)
    service = GeographicEnrichmentService()
    assert service.enrich(business) is business
    assert business.country_code == code
    assert business.state == state
    assert business.city is None
    assert business.district is None
    assert business.address == address
    service.enrich(business)
    if code:
        assert business.geographic_sources["country_code"] == ["formatted_address"]


def test_country_conflict_preserves_provider():
    business = map_serper_place(
        {"title": "Agency", "countryCode": "US", "address": "Street, Nepal"}
    )
    assert business.country_code == "US"
    assert business.geographic_conflicts
    assert business.geographic_sources["country_code"] == ["provider"]


def test_provider_conflict_not_hidden_by_address():
    business = map_serper_place(
        {
            "title": "Agency",
            "countryCode": "US",
            "country": "Nepal",
            "address": "Street, Nepal",
        }
    )
    assert business.country_code is None
    assert business.geographic_conflicts


def test_address_country_used_before_phone_normalization():
    business = map_serper_place(
        {"title": "Agency", "address": "Street, USA", "phoneNumber": "2025550123"},
        region="NP",
    )
    assert business.phone_numbers == ["+12025550123"]


def test_merge_preserves_geographic_evidence():
    first = Business(name="Agency", serper_cid="123")
    second = map_serper_place(
        {"title": "Agency", "cid": "123", "address": "Street, Nepal"}
    )
    result = BusinessDeduplicationService().merge_business(first, second)
    assert result.country_code == "NP"
    assert result.geographic_sources["country_code"] == ["formatted_address"]
    result.geographic_sources["country_code"].append("review")
    assert second.geographic_sources["country_code"] == ["formatted_address"]
