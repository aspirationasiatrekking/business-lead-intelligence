
import httpx
import respx

from src.lead_intelligence.scrapers.website_scraper import fetch_website
from src.lead_intelligence.scrapers.website_scraper import (
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

    respx.get(url).mock(
        return_value=httpx.Response(200, text=html)
    )

    result = fetch_website(url)

    assert result is not None
    assert "Welcome" in result
    assert "Business contact information" in result


@respx.mock
def test_fetch_website_http_error():

    url = "https://example.com"

    respx.get(url).mock(
        return_value=httpx.Response(404)
    )

    result = fetch_website(url)

    assert result is None



@respx.mock
def test_fetch_website_connection_error():

    url = "https://example.com"

    respx.get(url).mock(
        side_effect=httpx.ConnectError("Connection failed")
    )

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

    assert result == [
        "https://example.com/company-information"
    ]


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
