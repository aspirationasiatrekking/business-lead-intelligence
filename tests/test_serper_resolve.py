from unittest.mock import Mock

import pytest

from src.lead_intelligence.search.serper_provider import (
    SerperSearchProvider,
)


def test_resolve_links_sends_correct_request(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    original_results = {
        "places": [
            {
                "title": "Nepal Hiking Team",
                "website": "https://google.com/goto?url=example",
            }
        ]
    }

    resolved_results = {
        "places": [
            {
                "title": "Nepal Hiking Team",
                "website": "https://nepalhikingteam.com",
            }
        ]
    }

    mock_response = Mock()
    mock_response.json.return_value = resolved_results

    mock_post = Mock(return_value=mock_response)

    monkeypatch.setattr(provider.session, "post", mock_post)

    result = provider.resolve_links(original_results)

    assert result == resolved_results

    mock_post.assert_called_once_with(
        "https://google.serper.dev/resolve",
        json=original_results,
        headers={
            "X-API-KEY": "test-api-key",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    mock_response.raise_for_status.assert_called_once()


def test_resolve_links_raises_http_error(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("Resolve request failed")

    mock_post = Mock(return_value=mock_response)
    monkeypatch.setattr(provider.session, "post", mock_post)

    with pytest.raises(Exception, match="Resolve request failed"):
        provider.resolve_links(
            {
                "places": [
                    {
                        "title": "Example Business",
                        "website": "https://google.com/goto?url=example",
                    }
                ]
            }
        )


@pytest.mark.parametrize(
    "response_data",
    [
        [],
        None,
        "invalid response",
        {"unexpected": []},
        {"places": "invalid"},
        {"places": None},
    ],
)
def test_resolve_links_rejects_invalid_response_structure(
    monkeypatch,
    response_data,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    mock_response = Mock()
    mock_response.json.return_value = response_data

    monkeypatch.setattr(
        provider.session,
        "post",
        Mock(return_value=mock_response),
    )

    with pytest.raises(ValueError, match="Serper Places response"):
        provider.resolve_links(
            {
                "places": [
                    {
                        "title": "Example Business",
                        "website": "https://google.com/goto?url=example",
                    }
                ]
            }
        )

    provider.close()


@pytest.mark.parametrize(
    "results",
    [
        None,
        [],
        "invalid",
        {},
        {"places": None},
        {"places": "invalid"},
        {"places": {}},
    ],
)
def test_resolve_links_rejects_invalid_input(
    monkeypatch,
    results,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_post = Mock()

    monkeypatch.setattr(provider.session, "post", mock_post)

    try:
        with pytest.raises(
            ValueError,
            match="Serper Places response",
        ):
            provider.resolve_links(results)

        mock_post.assert_not_called()
    finally:
        provider.close()


def test_resolve_links_skips_empty_places(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_post = Mock()

    monkeypatch.setattr(provider.session, "post", mock_post)

    results = {"places": []}

    try:
        assert provider.resolve_links(results) == results

        mock_post.assert_not_called()
    finally:
        provider.close()


def test_resolve_links_skips_results_without_redirects(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_post = Mock()

    monkeypatch.setattr(provider.session, "post", mock_post)

    results = {
        "places": [
            {
                "title": "First Business",
                "website": "https://example.com",
            },
            {
                "title": "Second Business",
            },
        ]
    }

    try:
        assert provider.resolve_links(results) == results

        mock_post.assert_not_called()
    finally:
        provider.close()


def test_resolve_links_handles_malformed_records_without_redirects(
    monkeypatch,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_post = Mock()

    monkeypatch.setattr(provider.session, "post", mock_post)

    results = {
        "places": [
            None,
            "invalid record",
            {"website": 123},
            {"website": "https://[invalid"},
            {"title": "Valid Business"},
        ]
    }

    try:
        assert provider.resolve_links(results) == results

        mock_post.assert_not_called()
    finally:
        provider.close()


def test_resolve_links_preserves_metadata_when_skipping(
    monkeypatch,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_post = Mock()

    monkeypatch.setattr(provider.session, "post", mock_post)

    results = {
        "places": [
            {
                "title": "Example Business",
                "website": "https://example.com",
            }
        ],
        "searchParameters": {
            "q": "Travel agencies",
            "gl": "np",
        },
    }

    try:
        result = provider.resolve_links(results)

        assert result == results
        assert result["searchParameters"]["gl"] == "np"

        mock_post.assert_not_called()
    finally:
        provider.close()


@pytest.mark.parametrize(
    "invalid_record",
    [None, "Invalid record", 123, [], True],
)
def test_resolve_links_skips_mixed_malformed_batches(
    monkeypatch,
    invalid_record,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_post = Mock()

    monkeypatch.setattr(provider.session, "post", mock_post)

    results = {
        "places": [
            {"title": "First Business"},
            invalid_record,
            {
                "title": "Second Business",
                "website": "https://google.com/goto?url=example",
            },
        ],
        "searchParameters": {
            "q": "Travel agencies",
            "gl": "np",
        },
    }

    try:
        result = provider.resolve_links(results)

        assert result == results
        assert len(result["places"]) == 3
        assert result["places"][1] == invalid_record
        assert result["searchParameters"]["gl"] == "np"

        mock_post.assert_not_called()
    finally:
        provider.close()
