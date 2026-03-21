from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass
class PriceRecord:
    store_id: str
    product_key: str
    price_eur: float
    date: date
    source: str


class AustriaPriceProvider(Protocol):
    async def fetch_daily_prices(self, day: date) -> list[PriceRecord]:
        ...


class MockHeisspreiseProvider:
    """
    MVP stub for a future Austrian retail price integration.
    The parser keeps the payload model explicit so we can switch to
    a real API connector without changing business logic.
    """

    async def fetch_daily_prices(self, day: date) -> list[PriceRecord]:
        return [
            PriceRecord(
                store_id="spar-1010",
                product_key="apfel_kg",
                price_eur=2.49,
                date=day,
                source="mock-heisspreise",
            ),
            PriceRecord(
                store_id="hofer-1040",
                product_key="apfel_kg",
                price_eur=2.19,
                date=day,
                source="mock-heisspreise",
            ),
        ]
