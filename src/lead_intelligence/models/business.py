
from dataclasses import dataclass, field


@dataclass
class Business:
    name: str
    address: str | None = None
    emails: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    website: str | None = None
    category: str | None = None
