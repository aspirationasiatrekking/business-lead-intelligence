
import pytest
from unittest.mock import Mock

from src.lead_intelligence.search.serper_provider import (
    SerperSearchProvider,
)


def test_provider_requires_api_key(monkeypatch):
    monkeypatch.delenv("SERPER_API_KEY", raising=False)

    with pytest.raises(ValueError, match="SERPER_API_KEY is missing"):
        SerperSearchProvider()


def test_search_places_sends_correct_request(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    mock_response = Mock()
    mock_response.json.return_value = {
        "places": [
            {"title": "Nepal Hiking Team"}
        ]
    }

    mock_post = Mock(return_value=mock_response)

    monkeypatch.setattr(
        "src.lead_intelligence.search.serper_provider.requests.post",
        mock_post,
    )

    result = provider.search_places(
        query="Trekking companies in Nepal",
        country="np",
    )

    assert result == {
        "places": [
            {"title": "Nepal Hiking Team"}
        ]
    }

    mock_post.assert_called_once_with(
        "https://google.serper.dev/places",
        json={
            "q": "Trekking companies in Nepal",
            "hl": "en",
            "page": 1,
            "gl": "np",
        },
        headers={
            "X-API-KEY": "test-api-key",
            "Content-Type": "application/json",
        },
        timeout=30,
    )

    mock_response.raise_for_status.assert_called_once()


def test_search_places_without_country(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    mock_response = Mock()
    mock_response.json.return_value = {"places": []}

    mock_post = Mock(return_value=mock_response)

    monkeypatch.setattr(
        "src.lead_intelligence.search.serper_provider.requests.post",
        mock_post,
    )

    provider.search_places(
        query="Trekking companies",
    )

    assert mock_post.call_args.kwargs["json"] == {
        "q": "Trekking companies",
        "hl": "en",
        "page": 1,
    }


def test_search_places_raises_http_error(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = (
        Exception("API request failed")
    )

    monkeypatch.setattr(
        "src.lead_intelligence.search.serper_provider.requests.post",
        Mock(return_value=mock_response),
    )

    with pytest.raises(Exception, match="API request failed"):
        provider.search_places("Trekking companies")
