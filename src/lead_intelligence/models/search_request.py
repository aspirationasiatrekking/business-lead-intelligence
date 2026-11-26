from dataclasses import dataclass
from typing import ClassVar

from src.lead_intelligence.utils.country_utils import (
    get_country_name,
    validate_country_code,
)


@dataclass(frozen=True, slots=True)
class SearchRequest:
    """Validated input for a geographic business search."""

    DEFAULT_MAX_RESULTS: ClassVar[int] = 10
    MAX_ALLOWED_RESULTS: ClassVar[int] = 100

    MAX_CITY_LENGTH: ClassVar[int] = 100
    MAX_QUERY_LENGTH: ClassVar[int] = 250

    country_code: str
    city: str
    query: str

    max_results: int = DEFAULT_MAX_RESULTS

    def __post_init__(self) -> None:
        country_code = validate_country_code(self.country_code)

        city = self._normalize_text(
            value=self.city,
            field_name="City",
            max_length=self.MAX_CITY_LENGTH,
        )

        query = self._normalize_text(
            value=self.query,
            field_name="Search query",
            max_length=self.MAX_QUERY_LENGTH,
        )

        if not isinstance(self.max_results, int) or isinstance(self.max_results, bool):
            raise TypeError("Maximum results must be an integer")

        if not (1 <= self.max_results <= self.MAX_ALLOWED_RESULTS):
            raise ValueError(
                f"Maximum results must be between 1 and {self.MAX_ALLOWED_RESULTS}"
            )

        object.__setattr__(
            self,
            "country_code",
            country_code,
        )

        object.__setattr__(
            self,
            "city",
            city,
        )

        object.__setattr__(
            self,
            "query",
            query,
        )

    @staticmethod
    def _normalize_text(
        value: str,
        field_name: str,
        max_length: int,
    ) -> str:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")

        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError(f"{field_name} contains invalid characters")

        normalized = " ".join(value.split())

        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")

        if len(normalized) > max_length:
            raise ValueError(f"{field_name} cannot exceed {max_length} characters")

        return normalized

    @property
    def country_name(self) -> str:
        return get_country_name(self.country_code)

    @property
    def provider_country(self) -> str:
        return self.country_code.lower()

    @property
    def phone_region(self) -> str:
        return self.country_code

    @property
    def search_query(self) -> str:
        return f"{self.query} in {self.city}, {self.country_name}"

    @property
    def signature(self) -> tuple[str, str, str]:
        """Canonical search identity for future duplicate detection."""

        return (
            self.country_code,
            self.city.casefold(),
            self.query.casefold(),
        )
