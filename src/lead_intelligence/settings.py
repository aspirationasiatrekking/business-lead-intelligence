"""Explicit application configuration with conservative resource bounds."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True, slots=True)
class ApplicationSettings:
    serper_api_key: str | None = field(default=None, repr=False)
    serper_timeout: int = 30
    serper_rps: int = 1
    max_search_pages: int = 15
    max_no_progress_pages: int = 2
    max_contact_pages: int = 5
    output_dir: Path = Path("output")
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        for name, lower, upper in (
            ("serper_timeout", 1, 30),
            ("serper_rps", 1, 5),
            ("max_search_pages", 1, 15),
            ("max_no_progress_pages", 1, 2),
            ("max_contact_pages", 0, 5),
        ):
            value = getattr(self, name)
            if type(value) is not int or not lower <= value <= upper:
                raise ValueError(
                    f"{name} must be an integer between {lower} and {upper}"
                )
        if self.serper_api_key is not None and (
            not isinstance(self.serper_api_key, str)
            or not self.serper_api_key
            or any(not 33 <= ord(c) <= 126 for c in self.serper_api_key)
        ):
            raise ValueError("SERPER_API_KEY is invalid")
        if self.log_level not in {"INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Invalid LOG_LEVEL")
        if not isinstance(self.output_dir, Path):
            raise TypeError("output_dir must be a Path")

    @classmethod
    def load(cls, env_file: Path | None = None) -> "ApplicationSettings":
        values = dotenv_values(env_file, interpolate=False) if env_file else {}
        values.update(os.environ)

        def integer(name: str, default: int) -> int:
            value = values.get(name, str(default))
            if (
                not isinstance(value, str)
                or not value.isascii()
                or not value.isdecimal()
            ):
                raise ValueError(f"{name} must be an integer")
            return int(value)

        output = values.get("OUTPUT_DIR", "output")
        if not output or any(ord(c) < 32 for c in output):
            raise ValueError("Invalid OUTPUT_DIR")
        return cls(
            serper_api_key=values.get("SERPER_API_KEY"),
            serper_timeout=integer("SERPER_TIMEOUT_SECONDS", 30),
            serper_rps=integer("SERPER_REQUESTS_PER_SECOND", 1),
            max_search_pages=integer("SERPER_MAX_SEARCH_PAGES", 15),
            max_no_progress_pages=integer("SERPER_MAX_NO_PROGRESS_PAGES", 2),
            max_contact_pages=integer("MAX_CONTACT_PAGES", 5),
            output_dir=Path(output),
            log_level=values.get("LOG_LEVEL", "INFO"),
        )
