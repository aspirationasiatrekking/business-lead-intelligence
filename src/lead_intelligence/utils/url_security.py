from urllib.parse import urlparse


def is_safe_url(url: str | None) -> bool:
    if not url:
        return False

    try:
        parsed = urlparse(url)

        if parsed.scheme not in {"http", "https"}:
            return False

        return bool(parsed.hostname)

    except ValueError:
        return False
