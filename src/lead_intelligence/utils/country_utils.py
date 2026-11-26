def normalize_country_code(
    country: str | None,
) -> str | None:
    """Validate and normalize an optional two-letter country code."""
    if country is None:
        return None

    if not isinstance(country, str):
        raise TypeError("Country code must be a string")

    country = country.strip().lower()

    if len(country) != 2 or not country.isascii() or not country.isalpha():
        raise ValueError("Country code must contain two ASCII letters")

    return country
