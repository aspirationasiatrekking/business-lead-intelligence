import pycountry


def normalize_country_code(
    country: str | None,
) -> str | None:
    """Normalize an optional two-letter country code."""

    if country is None:
        return None

    if not isinstance(country, str):
        raise TypeError("Country code must be a string")

    country = country.strip().lower()

    if len(country) != 2 or not country.isascii() or not country.isalpha():
        raise ValueError("Country code must contain two ASCII letters")

    return country


def validate_country_code(country: str) -> str:
    """Validate an actual ISO 3166-1 alpha-2 country code."""

    normalized = normalize_country_code(country)

    if normalized is None:
        raise ValueError("Country code is required")

    country_record = pycountry.countries.get(alpha_2=normalized.upper())

    if country_record is None:
        raise ValueError(f"Unknown country code: {normalized.upper()}")

    return normalized.upper()


def get_country_name(country: str) -> str:
    """Return a readable country name from an ISO country code."""

    country_code = validate_country_code(country)

    country_record = pycountry.countries.get(alpha_2=country_code)

    return (
        getattr(
            country_record,
            "common_name",
            None,
        )
        or country_record.name
    )


def get_country_options() -> list[dict[str, str]]:
    """Return country options for a future frontend dropdown."""

    countries = [
        {
            "code": country.alpha_2,
            "name": (
                getattr(
                    country,
                    "common_name",
                    None,
                )
                or country.name
            ),
        }
        for country in pycountry.countries
    ]

    return sorted(
        countries,
        key=lambda country: country["name"].casefold(),
    )


def find_country_code(
    country_name: str | None,
) -> str | None:
    """Resolve an explicitly supplied country name or code."""

    if not isinstance(country_name, str):
        return None

    country_name = country_name.strip()

    if not country_name:
        return None

    try:
        country_record = pycountry.countries.lookup(country_name)

    except LookupError:
        return None

    return country_record.alpha_2
