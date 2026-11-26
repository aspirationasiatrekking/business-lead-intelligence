import time
from unittest.mock import Mock, patch

import httpx
import pytest

from src.lead_intelligence.scrapers.website_scraper import (
    MAX_RESPONSE_SIZE,
    DownloadDeadlineExceeded,
    ResponseTooLargeError,
    UnsupportedContentError,
    check_download_deadline,
    read_response_html,
    should_retry,
    validate_redirect_destination,
    validate_response_headers,
)

MODULE = "src.lead_intelligence.scrapers.website_scraper"


@pytest.mark.parametrize(
    "content_type",
    [
        "text/html",
        "text/html; charset=utf-8",
        "application/xhtml+xml",
        "text/plain",
        "TEXT/HTML",
        "",
    ],
)
def test_accepts_supported_content_types(content_type):
    response = httpx.Response(
        200,
        headers={"Content-Type": content_type},
    )

    validate_response_headers(response)


@pytest.mark.parametrize(
    "content_type",
    [
        "application/pdf",
        "application/zip",
        "application/json",
        "application/octet-stream",
        "image/png",
        "image/jpeg",
        "video/mp4",
        "audio/mpeg",
        "application/javascript",
    ],
)
def test_rejects_unsupported_content_types(content_type):
    response = httpx.Response(
        200,
        headers={"Content-Type": content_type},
    )

    with pytest.raises(UnsupportedContentError):
        validate_response_headers(response)


@pytest.mark.parametrize(
    "encoding",
    [
        "gzip",
        "deflate",
        "br",
        "zstd",
        "gzip, br",
    ],
)
def test_rejects_compressed_responses(encoding):
    response = httpx.Response(
        200,
        headers={"Content-Encoding": encoding},
    )

    with pytest.raises(UnsupportedContentError):
        validate_response_headers(response)


@pytest.mark.parametrize(
    "encoding",
    [
        "",
        "identity",
        "IDENTITY",
    ],
)
def test_accepts_uncompressed_responses(encoding):
    response = httpx.Response(
        200,
        headers={"Content-Encoding": encoding},
    )

    validate_response_headers(response)


@pytest.mark.parametrize(
    "content_length",
    [
        "-1",
        "invalid",
        "1.5",
        "1e6",
        "+100",
        "100, 200",
        "",
    ],
)
def test_rejects_invalid_content_length(
    content_length,
):
    response = httpx.Response(
        200,
        headers={"Content-Length": content_length},
    )

    with pytest.raises(
        ValueError,
        match="Invalid Content-Length",
    ):
        validate_response_headers(response)


def test_rejects_oversized_content_length():
    response = httpx.Response(
        200,
        headers={"Content-Length": str(MAX_RESPONSE_SIZE + 1)},
    )

    with pytest.raises(ResponseTooLargeError):
        validate_response_headers(response)


@pytest.mark.parametrize(
    "size",
    [
        0,
        1,
        1024,
        MAX_RESPONSE_SIZE,
    ],
)
def test_accepts_valid_content_lengths(size):
    response = httpx.Response(
        200,
        headers={"Content-Length": str(size)},
    )

    validate_response_headers(response)


def test_reads_valid_html_response():
    response = httpx.Response(
        200,
        content=b"<html>Example</html>",
    )

    result = read_response_html(
        response,
        deadline=time.monotonic() + 10,
    )

    assert result == "<html>Example</html>"


def test_rejects_oversized_stream_without_content_length():
    response = Mock(spec=httpx.Response)

    response.headers = httpx.Headers()

    response.iter_bytes.return_value = [
        b"x" * MAX_RESPONSE_SIZE,
        b"x",
    ]

    with pytest.raises(ResponseTooLargeError):
        read_response_html(
            response,
            deadline=time.monotonic() + 10,
        )


def test_accepts_stream_at_exact_size_limit():
    response = httpx.Response(
        200,
        content=b"x" * MAX_RESPONSE_SIZE,
    )

    result = read_response_html(
        response,
        deadline=time.monotonic() + 10,
    )

    assert len(result) == MAX_RESPONSE_SIZE


def test_response_headers_checked_before_streaming():
    response = Mock(spec=httpx.Response)

    response.headers = httpx.Headers({"Content-Type": "application/pdf"})

    with pytest.raises(UnsupportedContentError):
        read_response_html(
            response,
            deadline=time.monotonic() + 10,
        )

    response.iter_bytes.assert_not_called()


def test_deadline_allows_remaining_time():
    check_download_deadline(time.monotonic() + 10)


def test_deadline_rejects_expired_budget():
    with pytest.raises(DownloadDeadlineExceeded):
        check_download_deadline(time.monotonic() - 1)


def test_expired_deadline_prevents_stream_reading():
    response = Mock(spec=httpx.Response)

    with pytest.raises(DownloadDeadlineExceeded):
        read_response_html(
            response,
            deadline=time.monotonic() - 1,
        )

    response.iter_bytes.assert_not_called()


def test_deadline_is_checked_during_streaming():
    response = Mock(spec=httpx.Response)

    response.headers = httpx.Headers()

    response.iter_bytes.return_value = [
        b"first",
        b"second",
    ]

    with (
        patch(
            f"{MODULE}.time.monotonic",
            side_effect=[
                0,
                1,
                11,
            ],
        ),
        pytest.raises(DownloadDeadlineExceeded),
    ):
        read_response_html(
            response,
            deadline=10,
        )


@pytest.mark.parametrize(
    ("original", "location", "expected"),
    [
        (
            "https://example.com",
            "/contact",
            "https://example.com/contact",
        ),
        (
            "http://example.com",
            "https://example.com",
            "https://example.com",
        ),
        (
            "https://example.com",
            "https://another-example.com",
            "https://another-example.com",
        ),
        (
            "https://example.com",
            "/contact#team",
            "https://example.com/contact",
        ),
    ],
)
def test_accepts_valid_redirects(
    original,
    location,
    expected,
):
    with patch(
        f"{MODULE}.is_safe_url",
        return_value=True,
    ):
        result = validate_redirect_destination(
            original,
            location,
        )

    assert result == expected


@pytest.mark.parametrize(
    "location",
    [
        "",
        " ",
        None,
        123,
        "ftp://example.com",
        "https://user@example.com",
        "https://[invalid",
        "https://example.com\\contact",
        "https://exam\nple.com",
        "http://example.com",
    ],
)
def test_rejects_invalid_redirects(location):
    with (
        patch(f"{MODULE}.is_safe_url") as mock_safe,
        pytest.raises(ValueError),
    ):
        validate_redirect_destination(
            "https://example.com",
            location,
        )

    mock_safe.assert_not_called()


def test_rejects_private_redirect_destination():
    with (
        patch(
            f"{MODULE}.is_safe_url",
            return_value=False,
        ),
        pytest.raises(
            ValueError,
            match="Unsafe redirect",
        ),
    ):
        validate_redirect_destination(
            "https://example.com",
            "https://127.0.0.1",
        )


@pytest.mark.parametrize(
    "status_code",
    [
        429,
        500,
        502,
        503,
        504,
    ],
)
def test_retries_temporary_http_errors(status_code):
    request = httpx.Request(
        "GET",
        "https://example.com",
    )

    response = httpx.Response(
        status_code,
        request=request,
    )

    error = httpx.HTTPStatusError(
        "Temporary failure",
        request=request,
        response=response,
    )

    assert should_retry(error) is True


@pytest.mark.parametrize(
    "status_code",
    [
        400,
        401,
        403,
        404,
        406,
        409,
        410,
        422,
    ],
)
def test_does_not_retry_permanent_http_errors(status_code):
    request = httpx.Request(
        "GET",
        "https://example.com",
    )

    response = httpx.Response(
        status_code,
        request=request,
    )

    error = httpx.HTTPStatusError(
        "Request rejected",
        request=request,
        response=response,
    )

    assert should_retry(error) is False


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectTimeout("Timeout"),
        httpx.ReadTimeout("Timeout"),
        httpx.ConnectError("Connection failed"),
        httpx.ReadError("Read failed"),
        httpx.WriteError("Write failed"),
        httpx.RemoteProtocolError("Protocol failed"),
    ],
)
def test_retries_temporary_network_errors(error):
    assert should_retry(error) is True


@pytest.mark.parametrize(
    "error",
    [
        ValueError("Unsafe URL"),
        UnsupportedContentError("Unsupported content"),
        ResponseTooLargeError("Too large"),
        DownloadDeadlineExceeded("Deadline exceeded"),
        httpx.UnsupportedProtocol("Invalid protocol"),
        httpx.LocalProtocolError("Invalid request"),
    ],
)
def test_does_not_retry_security_failures(error):
    assert should_retry(error) is False
