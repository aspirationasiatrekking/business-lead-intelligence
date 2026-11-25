
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

    monkeypatch.setattr(provider.session, "post", mock_post)

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
            "num": 10,
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

    monkeypatch.setattr(provider.session, "post", mock_post)

    provider.search_places(
        query="Trekking companies",
    )

    assert mock_post.call_args.kwargs["json"] == {
        "q": "Trekking companies",
        "hl": "en",
        "num": 10,
        "page": 1,
    }


def test_search_places_raises_http_error(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    mock_response = Mock()
    mock_response.raise_for_status.side_effect = (
        Exception("API request failed")
    )

    monkeypatch.setattr(provider.session, "post", Mock(return_value=mock_response)) 

    with pytest.raises(Exception, match="API request failed"):
        provider.search_places("Trekking companies")



import pytest
import requests

from src.lead_intelligence.search.serper_provider import (
    SerperSearchProvider,
)


@pytest.mark.parametrize(
    "query",
    ["", "   ", "\t", "\n"],
)


def test_rejects_empty_or_whitespace_queries(
    monkeypatch,
    query,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    def unexpected_request(*args, **kwargs):
        pytest.fail("API request should not be made")

    monkeypatch.setattr(
        provider.session,
        "post",
        unexpected_request,
    )

    with pytest.raises(
        ValueError,
        match="Search query cannot be empty",
    ):
        provider.search_places(query)

    provider.close()


@pytest.mark.parametrize("page", [0, -1, -10])
def test_rejects_invalid_page_numbers(
    monkeypatch,
    page,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    def unexpected_request(*args, **kwargs):
        pytest.fail("API request should not be made")

    monkeypatch.setattr(
        provider.session,
        "post",
        unexpected_request,
    )

    with pytest.raises(
        ValueError,
        match="Page must be greater than or equal to 1",
    ):
        provider.search_places("Trekking companies", page=page)

    provider.close()


@pytest.mark.parametrize("page", [1.5, "2", True, False, None])
def test_rejects_non_integer_page_numbers(
    monkeypatch,
    page,
):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    def unexpected_request(*args, **kwargs):
        pytest.fail("API request should not be made")

    monkeypatch.setattr(
        provider.session,
        "post",
        unexpected_request,
    )

    with pytest.raises(
        ValueError,
        match="Page must be an integer",
    ):
        provider.search_places("Trekking companies", page=page)

    provider.close()
from requests_ratelimiter import LimiterSession


def test_provider_uses_rate_limited_session(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    assert isinstance(provider.session, LimiterSession)
    assert provider.REQUESTS_PER_SECOND == 1

    provider.close()


def test_search_places_with_custom_num(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()
    mock_response = Mock()
    mock_response.json.return_value = {"places": []}

    mock_post = Mock(return_value=mock_response)
    monkeypatch.setattr(provider.session, "post", mock_post)

    provider.search_places(
        query="Trekking companies",
        num=50,
    )

    assert mock_post.call_args.kwargs["json"]["num"] == 50
    provider.close()


@pytest.mark.parametrize("num", [0, -1, 101])
def test_rejects_invalid_num_values(monkeypatch, num):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    def unexpected_request(*args, **kwargs):
        pytest.fail("API request should not be made")

    monkeypatch.setattr(provider.session, "post", unexpected_request)

    with pytest.raises(
        ValueError,
        match="Number of results must be between 1 and 100",
    ):
        provider.search_places("Trekking companies", num=num)

    provider.close()

@pytest.mark.parametrize("num", [1.5, "10", True, False, None])
def test_rejects_non_integer_num(monkeypatch, num):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    provider = SerperSearchProvider()

    def unexpected_request(*args, **kwargs):
        pytest.fail("API request should not be made")

    monkeypatch.setattr(provider.session, "post", unexpected_request)

    with pytest.raises(
        ValueError,
        match="Number of results must be an integer",
    ):
        provider.search_places("Trekking companies", num=num)

    provider.close()