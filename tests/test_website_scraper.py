from unittest.mock import patch

import httpx
import respx

from src.lead_intelligence.scrapers.website_scraper import (
    MAX_RESPONSE_SIZE,
    fetch_website,
    fetch_website_html,
    find_contact_pages,
)


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
