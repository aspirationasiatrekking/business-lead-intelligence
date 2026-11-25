
import pytest
from unittest.mock import Mock

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
    mock_response.raise_for_status.side_effect = (
        Exception("Resolve request failed")
    )

    mock_post = Mock(return_value=mock_response)
    monkeypatch.setattr(provider.session, "post", mock_post)

    with pytest.raises(Exception, match="Resolve request failed"):
        provider.resolve_links({"places": []})
