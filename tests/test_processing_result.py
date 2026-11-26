from src.lead_intelligence.models.business import Business
from src.lead_intelligence.models.processing_result import (
    MappingResult,
    ProcessingFailure,
    SearchResult,
)


def test_mapping_result_defaults():
    result = MappingResult()

    assert result.businesses == []
    assert result.failures == []
    assert result.total_processed == 0


def test_mapping_result_total_processed():
    result = MappingResult(
        businesses=[
            Business(name="First Business"),
            Business(name="Second Business"),
        ],
        failures=[
            ProcessingFailure(
                item_index=2,
                stage="mapping",
                message="Invalid record",
            )
        ],
    )

    assert result.total_processed == 3


def test_search_result_defaults():
    result = SearchResult()

    assert result.businesses == []
    assert result.failures == []
    assert result.total_discovered == 0
    assert result.total_mapped == 0
    assert result.duplicate_count == 0
    assert result.total_returned == 0
    assert result.total_failed == 0
    assert result.has_failures is False


def test_search_result_with_successful_businesses():
    result = SearchResult(
        businesses=[
            Business(name="First Business"),
            Business(name="Second Business"),
        ],
        total_discovered=2,
        total_mapped=2,
    )

    assert result.total_returned == 2
    assert result.total_failed == 0
    assert result.has_failures is False


def test_search_result_with_mapping_failures():
    result = SearchResult(
        businesses=[
            Business(name="Valid Business"),
        ],
        failures=[
            ProcessingFailure(
                item_index=1,
                stage="mapping",
                message="Invalid business data",
                item_name="Broken Business",
            )
        ],
        total_discovered=2,
        total_mapped=1,
    )

    assert result.total_returned == 1
    assert result.total_failed == 1
    assert result.has_failures is True


def test_search_result_with_duplicates():
    result = SearchResult(
        businesses=[
            Business(name="First Business"),
            Business(name="Second Business"),
        ],
        total_discovered=4,
        total_mapped=4,
        duplicate_count=2,
    )

    assert result.total_discovered == 4
    assert result.total_mapped == 4
    assert result.duplicate_count == 2
    assert result.total_returned == 2
    assert result.total_failed == 0


def test_search_result_lists_are_independent():
    first = SearchResult()
    second = SearchResult()

    first.businesses.append(Business(name="Example Business"))

    first.failures.append(
        ProcessingFailure(
            item_index=1,
            stage="mapping",
            message="Invalid record",
        )
    )

    assert second.businesses == []
    assert second.failures == []


def test_search_result_returned_count_reflects_list_changes():
    result = SearchResult()

    assert result.total_returned == 0

    result.businesses.append(Business(name="Example Business"))

    assert result.total_returned == 1


def test_search_result_failure_count_reflects_list_changes():
    result = SearchResult()

    assert result.total_failed == 0
    assert result.has_failures is False

    result.failures.append(
        ProcessingFailure(
            item_index=0,
            stage="mapping",
            message="Invalid record",
        )
    )

    assert result.total_failed == 1
    assert result.has_failures is True
