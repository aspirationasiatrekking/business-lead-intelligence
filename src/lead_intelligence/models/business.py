
from dataclasses import dataclass


@dataclass
class Business:
    name: str
    address: str | None = None
    phone: str | None = None
    website: str | None = None
    category: str | None = None
