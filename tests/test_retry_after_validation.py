from datetime import UTC, datetime, timedelta
from email.utils import format_datetime
from unittest.mock import Mock

import pytest
import requests

from src.lead_intelligence.search.serper_provider import (
    get_retry_after_seconds,
    wait_for_retry,
)


def make_http_error(
    status_code=429,
    retry_after=None,
):
    response = requests.Response()
    response.status_code = status_code

    if retry_after is not None:
        response.headers["Retry-After"] = retry_after

    return requests.exceptions.HTTPError(
        f"HTTP {status_code}",
        response=response,
    )


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("0", 0.0),
        ("1", 1.0),
        ("5", 5.0),
        ("2.5", 2.5),
        (" 10 ", 10.0),
        ("-5", 0.0),
        ("100", 100.0),
    ],
)
def test_retry_after_accepts_finite_delays(
    header,
    expected,
):
    error = make_http_error(retry_after=header)

    assert get_retry_after_seconds(error) == expected


@pytest.mark.parametrize(
    "header",
    [
        "nan",
        "NaN",
        "inf",
        "+inf",
        "-inf",
        "Infinity",
        "-Infinity",
        "1e309",
    ],
)
def test_retry_after_rejects_non_finite_values(header):
    error = make_http_error(retry_after=header)

    assert get_retry_after_seconds(error) is None


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        " ",
        "invalid",
        "invalid date",
    ],
)
def test_retry_after_rejects_invalid_headers(header):
    error = make_http_error(retry_after=header)

    assert get_retry_after_seconds(error) is None


@pytest.mark.parametrize(
    "status_code",
    [400, 401, 403, 404, 500, 502, 503, 504],
)
def test_retry_after_ignores_other_status_codes(
    status_code,
):
    error = make_http_error(
        status_code=status_code,
        retry_after="10",
    )

    assert get_retry_after_seconds(error) is None


def test_retry_after_handles_http_error_without_response():
    error = requests.exceptions.HTTPError("No response")

    assert get_retry_after_seconds(error) is None


def test_retry_after_handles_non_http_error():
    error = requests.exceptions.Timeout("Request timed out")

    assert get_retry_after_seconds(error) is None


def test_retry_after_accepts_future_http_date():
    future = datetime.now(UTC) + timedelta(seconds=60)

    error = make_http_error(
        retry_after=format_datetime(
            future,
            usegmt=True,
        ),
    )

    delay = get_retry_after_seconds(error)

    assert delay is not None
    assert 55 <= delay <= 60


def test_retry_after_clamps_past_http_date():
    past = datetime.now(UTC) - timedelta(seconds=60)

    error = make_http_error(
        retry_after=format_datetime(
            past,
            usegmt=True,
        ),
    )

    assert get_retry_after_seconds(error) == 0.0


def test_wait_for_retry_caps_large_delays():
    error = make_http_error(retry_after="120")

    retry_state = Mock()
    retry_state.outcome.exception.return_value = error
    retry_state.attempt_number = 1

    assert wait_for_retry(retry_state) == 30.0


def test_wait_for_retry_respects_valid_delay():
    error = make_http_error(retry_after="5")

    retry_state = Mock()
    retry_state.outcome.exception.return_value = error
    retry_state.attempt_number = 1

    assert wait_for_retry(retry_state) == 5.0


@pytest.mark.parametrize(
    ("attempt_number", "expected"),
    [
        (1, 1.0),
        (2, 2.0),
        (3, 4.0),
        (4, 8.0),
        (5, 8.0),
    ],
)
def test_wait_for_retry_uses_exponential_backoff(
    attempt_number,
    expected,
):
    error = make_http_error(retry_after="nan")

    retry_state = Mock()
    retry_state.outcome.exception.return_value = error
    retry_state.attempt_number = attempt_number

    assert wait_for_retry(retry_state) == expected
