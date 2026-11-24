
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse


CONTACT_KEYWORDS = {
    "contact",
    "contact-us",
    "about",
    "about-us",
    "reach-us",
}


def fetch_website_html(url: str) -> str | None:
    try:
        response = httpx.get(url, timeout=15)
        response.raise_for_status()
        return response.text

    except (httpx.HTTPError, httpx.InvalidURL):
        print(f"Error fetching website: {url}")
        return None


def extract_website_text(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for element in soup(["script", "style", "noscript", "svg"]):
        element.decompose()

    return soup.get_text(separator="\n", strip=True)


def fetch_website(url: str) -> str | None:
    html = fetch_website_html(url)

    if html is None:
        return None

    return extract_website_text(html)


def find_contact_pages(url: str, html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")

    contact_pages = []
    homepage = urlparse(url)

    for link in soup.find_all("a", href=True):
        href = link["href"]

        full_url = urljoin(url, href)
        parsed_url = urlparse(full_url)

        if parsed_url.scheme not in {"http", "https"}:
            continue

        if parsed_url.netloc.lower() != homepage.netloc.lower():
            continue

        if parsed_url.path.rstrip("/") == homepage.path.rstrip("/"):
            continue

        link_text = link.get_text(strip=True).lower()

        searchable_text = (
            link_text + " " + parsed_url.path.lower()
        )

        if any(
            keyword in searchable_text
            for keyword in CONTACT_KEYWORDS
        ):
            if full_url not in contact_pages:
                contact_pages.append(full_url)

    return contact_pages
