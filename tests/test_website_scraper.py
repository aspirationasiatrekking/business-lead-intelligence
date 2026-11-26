import socket
from unittest.mock import patch

import httpx
import pytest
import respx

from src.lead_intelligence.scrapers.website_scraper import (
    MAX_RESPONSE_SIZE,
    create_secure_client,
    fetch_website,
    fetch_website_html,
    find_contact_pages,
)
from src.lead_intelligence.utils.secure_transport import (
    SecureHTTPTransport,
    UnsafeDestinationError,
)


@pytest.fixture(autouse=True)
def mock_website_dns(monkeypatch):
    """Prevent scraper unit tests from using real DNS services."""

    def fake_getaddrinfo(
        host,
        port,
        *args,
        **kwargs,
    ):
        return [
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("8.8.8.8", port),
            )
        ]

    monkeypatch.setattr(
        "src.lead_intelligence.utils.url_utils.socket.getaddrinfo",
        fake_getaddrinfo,
    )


def test_fetch_website_disables_environment_proxies():
    with patch(
        "src.lead_intelligence.scrapers.website_scraper.httpx.Client"
    ) as mock_client:
        from src.lead_intelligence.scrapers.website_scraper import (
            create_secure_client,
        )

        create_secure_client()

    kwargs = mock_client.call_args.kwargs

    assert kwargs["trust_env"] is False
    assert kwargs["follow_redirects"] is False

    from src.lead_intelligence.utils.secure_transport import (
        SecureHTTPTransport,
    )

    assert isinstance(
        kwargs["transport"],
        SecureHTTPTransport,
    )

    kwargs["transport"].close()


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1",
        "http://192.168.0.1",
        "http://169.254.169.254",
        "http://[::1]",
        "https://example.com:6379",
        "ftp://example.com",
        "https://user@example.com",
    ],
)
def test_unsafe_destination_never_reaches_httpx(url):
    with patch(
        "src.lead_intelligence.scrapers.website_scraper.create_secure_client"
    ) as mock_client:
        result = fetch_website_html(url)

    assert result is None
    mock_client.assert_not_called()


@respx.mock
def test_fetch_website_success():

    url = "https://example.com"

    html = """
    <html>
        <head><title>Example</title></head>
        <body>
            <h1>Welcome</h1>
            <p>Business contact information</p>
        </body>
    </html>
    """

    respx.get(url).mock(return_value=httpx.Response(200, text=html))

    result = fetch_website(url)

    assert result is not None
    assert "Welcome" in result
    assert "Business contact information" in result


@respx.mock
def test_fetch_website_http_error():

    url = "https://example.com"

    respx.get(url).mock(return_value=httpx.Response(404))

    result = fetch_website(url)

    assert result is None


@respx.mock
def test_fetch_website_connection_error():

    url = "https://example.com"

    respx.get(url).mock(side_effect=httpx.ConnectError("Connection failed"))

    result = fetch_website(url)

    assert result is None


def test_find_contact_pages(respx_mock):
    html = """
    <html>
        <body>
            <a href="/contact">Contact Us</a>
            <a href="/about">About Us</a>
            <a href="https://facebook.com/example">Facebook</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == [
        "https://example.com/contact",
        "https://example.com/about",
    ]


def test_find_contact_pages_from_link_text(respx_mock):
    html = """
    <html>
        <body>
            <a href="/company-information">About Our Company</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == ["https://example.com/company-information"]


def test_find_contact_pages_removes_duplicates(respx_mock):
    html = """
    <html>
        <body>
            <a href="/contact">Contact Us</a>
            <a href="/contact">Get In Touch</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == ["https://example.com/contact"]


def test_find_contact_pages_no_results(respx_mock):
    html = """
    <html>
        <body>
            <a href="/services">Our Services</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == []


def test_find_contact_pages_invalid_scheme(respx_mock):
    html = """
    <html>
        <body>
            <a href="javascript:void(0)">Contact Us</a>
            <a href="mailto:info@example.com">Email Us</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == []


def test_find_contact_pages_with_get_in_touch():
    html = """
    <html>
        <body>
            <a href="/reach-us">Get In Touch</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == ["https://example.com/reach-us"]


def test_find_contact_pages_with_support():
    html = """
    <html>
        <body>
            <a href="/support">Customer Support</a>
        </body>
    </html>
    """

    result = find_contact_pages("https://example.com", html)

    assert result == ["https://example.com/support"]


@respx.mock
@patch(
    "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
    return_value=True,
)
def test_fetch_website_rejects_oversized_content_length(mock_safe_url):

    url = "https://example.com"

    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Length": str(MAX_RESPONSE_SIZE + 1)},
            content=b"small response",
        )
    )

    result = fetch_website_html(url)

    assert result is None


@respx.mock
@patch(
    "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
    return_value=True,
)
def test_fetch_website_rejects_oversized_stream(mock_safe_url):

    url = "https://example.com"

    large_content = b"x" * (MAX_RESPONSE_SIZE + 1)

    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            content=large_content,
        )
    )

    result = fetch_website_html(url)

    assert result is None


@respx.mock
@patch(
    "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
    return_value=True,
)
def test_fetch_website_accepts_response_under_size_limit(mock_safe_url):

    url = "https://example.com"

    content = b"<html><body>Welcome</body></html>"

    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            content=content,
        )
    )

    result = fetch_website_html(url)

    assert result is not None
    assert "Welcome" in result


# =========================================================
# REDIRECT SECURITY TESTS
# =========================================================


@respx.mock
@patch(
    "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
    return_value=True,
)
def test_fetch_website_follows_relative_redirect(mock_safe_url):

    original_url = "https://example.com/"
    redirected_url = "https://example.com/contact"

    respx.get(original_url).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "/contact"},
        )
    )

    respx.get(redirected_url).mock(
        return_value=httpx.Response(
            200,
            text="<html><body>Contact page</body></html>",
        )
    )

    result = fetch_website_html(original_url)

    assert result is not None
    assert "Contact page" in result
    assert respx.get(original_url).called
    assert respx.get(redirected_url).called


@respx.mock
@patch(
    "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
)
def test_fetch_website_rejects_unsafe_redirect(mock_safe_url):

    original_url = "https://example.com"
    private_url = "http://127.0.0.1"

    mock_safe_url.side_effect = [True, False]

    respx.get(original_url).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": private_url},
        )
    )

    result = fetch_website_html(original_url)

    assert result is None
    assert not respx.get(private_url).called


@respx.mock
@patch(
    "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
    return_value=True,
)
def test_fetch_website_rejects_too_many_redirects(mock_safe_url):

    url = "https://example.com"

    route = respx.get(url).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": "/redirect"},
        )
    )

    result = fetch_website_html(url)

    assert result is None
    assert route.call_count == 6


def test_secure_client_can_be_created_and_closed():
    with create_secure_client() as client:
        assert isinstance(client, httpx.Client)

        assert isinstance(
            client._transport,
            SecureHTTPTransport,
        )


def test_unsafe_connection_is_handled_without_retry():
    url = "https://example.com"

    with (
        patch(
            "src.lead_intelligence.scrapers.website_scraper.is_safe_url",
            return_value=True,
        ),
        patch(
            "src.lead_intelligence.scrapers.website_scraper.create_secure_client"
        ) as mock_factory,
    ):
        client = mock_factory.return_value.__enter__.return_value

        client.stream.side_effect = UnsafeDestinationError("Connection blocked")

        result = fetch_website_html(url)

    assert result is None
    assert mock_factory.call_count == 1


@respx.mock
def test_fetch_website_handles_unknown_encoding():
    url = "https://example.com"

    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": ("text/html; charset=unknown-encoding")},
            content=b"<html>Example</html>",
        )
    )

    result = fetch_website_html(url)

    assert result == "<html>Example</html>"


@respx.mock
def test_scraper_rejects_pdf_response():
    url = "https://example.com"

    route = respx.get(url).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "application/pdf"},
            content=b"%PDF-1.7",
        )
    )

    assert fetch_website_html(url) is None
    assert route.call_count == 1


@respx.mock
def test_scraper_rejects_https_downgrade():
    original = "https://example.com"
    destination = "http://example.com"

    respx.get(original).mock(
        return_value=httpx.Response(
            302,
            headers={"Location": destination},
        )
    )

    destination_route = respx.get(destination).mock(
        return_value=httpx.Response(
            200,
            text="<html>Example</html>",
        )
    )

    assert fetch_website_html(original) is None
    assert not destination_route.called


@respx.mock
def test_scraper_allows_http_upgrade():
    original = "http://example.com"
    destination = "https://example.com"

    respx.get(original).mock(
        return_value=httpx.Response(
            301,
            headers={"Location": destination},
        )
    )

    respx.get(destination).mock(
        return_value=httpx.Response(
            200,
            headers={"Content-Type": "text/html"},
            text="<html>Secure website</html>",
        )
    )

    assert fetch_website_html(original) == ("<html>Secure website</html>")


@respx.mock
def test_scraper_rejects_redirect_without_location():
    url = "https://example.com"

    route = respx.get(url).mock(return_value=httpx.Response(302))

    assert fetch_website_html(url) is None
    assert route.call_count == 1


@respx.mock
def test_scraper_requests_uncompressed_content():
    url = "https://example.com"

    route = respx.get(url).mock(
        return_value=httpx.Response(
            200,
            text="<html>Example</html>",
        )
    )

    assert fetch_website_html(url) is not None

    request = route.calls.last.request

    assert request.headers["accept-encoding"] == "identity"
