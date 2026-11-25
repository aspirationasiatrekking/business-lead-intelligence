from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import requests

from src.lead_intelligence.search.serper_provider import (
    SerperSearchProvider,
    get_retry_after_seconds,
    wait_for_retry,
)


@pytest.fixture
def provider(monkeypatch):
    monkeypatch.setenv("SERPER_API_KEY", "test-api-key")

    instance = SerperSearchProvider()

    # Prevent real waiting during retry tests.
    instance._post.retry.sleep = lambda _: None

    return instance


def make_http_error(status_code):
    response = requests.Response()
    response.status_code = status_code

    return requests.exceptions.HTTPError(
        f"HTTP {status_code}",
        response=response,
    )


@pytest.mark.parametrize(
    "error",
    [
        requests.exceptions.Timeout("Request timed out"),
        requests.exceptions.ConnectionError("Connection failed"),
    ],
)
def test_retries_connection_errors(provider, monkeypatch, error):

    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)

        if len(calls) == 1:
            raise error

        response = requests.Response()
        response.status_code = 200
        response._content = b'{"places": []}'

        return response

    monkeypatch.setattr(provider.session, "post", fake_post)

    result = provider.search_places("Trekking companies")

    assert result == {"places": []}
    assert len(calls) == 2


@pytest.mark.parametrize(
    "status_code",
    [429, 500, 502, 503, 504],
)
def test_retries_temporary_http_errors(
    provider,
    monkeypatch,
    status_code,
):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)

        if len(calls) < 3:
            raise make_http_error(status_code)

        response = requests.Response()
        response.status_code = 200
        response._content = b'{"places": []}'

        return response

    monkeypatch.setattr(provider.session, "post", fake_post)

    result = provider.search_places("Trekking companies")

    assert result == {"places": []}
    assert len(calls) == 3


def test_stops_after_three_failed_attempts(
    provider,
    monkeypatch,
):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        raise requests.exceptions.Timeout("Request timed out")

    monkeypatch.setattr(provider.session, "post", fake_post)

    with pytest.raises(requests.exceptions.Timeout):
        provider.search_places("Trekking companies")

    assert len(calls) == 3


def test_does_not_retry_permanent_http_errors(
    provider,
    monkeypatch,
):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append(1)
        raise make_http_error(400)

    monkeypatch.setattr(provider.session, "post", fake_post)

    with pytest.raises(requests.exceptions.HTTPError):
        provider.search_places("Trekking companies")

    assert len(calls) == 1


def test_retry_after_numeric_header():
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "5"

    error = requests.exceptions.HTTPError(
        "HTTP 429",
        response=response,
    )

    assert get_retry_after_seconds(error) == 5.0


def test_retry_after_http_date():
    future_date = datetime.now(UTC) + timedelta(seconds=10)

    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = format_datetime(future_date)

    error = requests.exceptions.HTTPError(
        "HTTP 429",
        response=response,
    )

    delay = get_retry_after_seconds(error)

    assert delay is not None
    assert 0 <= delay <= 10


def test_retry_after_missing_or_invalid_header():
    response = requests.Response()
    response.status_code = 429

    error = requests.exceptions.HTTPError(
        "HTTP 429",
        response=response,
    )

    assert get_retry_after_seconds(error) is None

    response.headers["Retry-After"] = "invalid-value"

    assert get_retry_after_seconds(error) is None


def test_retry_after_is_capped_at_30_seconds():
    response = requests.Response()
    response.status_code = 429
    response.headers["Retry-After"] = "120"

    error = requests.exceptions.HTTPError(
        "HTTP 429",
        response=response,
    )

    retry_state = Mock()
    retry_state.outcome.exception.return_value = error

    assert wait_for_retry(retry_state) == 30.0
