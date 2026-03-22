from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol

import httpx


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


def _normalize_store_id(raw_store: str) -> str:
    return raw_store.strip().lower().replace(" ", "-")


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


class HeisspreiseLiveProvider:
    """
    Real Austrian supermarket source based on heisse-preise.io compressed
    canonical datasets used by the public frontend.
    """

    BASE_URL = "https://heisse-preise.io/data/latest-canonical.{store}.compressed.json"
    DEFAULT_STORE_KEYS = ("billa", "spar", "lidl")

    def __init__(self, store_keys: tuple[str, ...] | None = None):
        self.store_keys = store_keys or self.DEFAULT_STORE_KEYS

    @staticmethod
    def _decode_date_token(token: str | int) -> date:
        token_str = str(token)
        return date.fromisoformat(
            f"{token_str[0:4]}-{token_str[4:6]}-{token_str[6:8]}"
        )

    @staticmethod
    def _lookup(container: list | dict, index: int | str):
        if isinstance(container, dict):
            if index in container:
                return container[index]
            return container[str(index)]
        return container[index]

    @classmethod
    def _decompress_records(cls, payload: dict, query_day: date) -> list[PriceRecord]:
        stores = payload.get("stores", [])
        data = payload.get("data", [])
        dates = payload.get("dates", [])
        num_items = payload.get("n", 0)

        result: list[PriceRecord] = []
        i = 0
        for _ in range(num_items):
            store = cls._lookup(stores, data[i])
            i += 1
            _product_id = data[i]
            i += 1
            name = str(data[i]).replace("M & M", "M&M")
            i += 1
            _category = data[i]
            i += 1
            _unavailable = data[i] == 1
            i += 1
            price_history_len = data[i]
            i += 1

            history: list[tuple[date, float]] = []
            for _history_idx in range(price_history_len):
                history_date = cls._decode_date_token(cls._lookup(dates, data[i]))
                i += 1
                amount = float(data[i])
                i += 1
                history.append((history_date, amount))

            unit = data[i]
            i += 1
            _quantity = data[i]
            i += 1
            _is_weighted = data[i] == 1
            i += 1
            _is_bio = data[i] == 1
            i += 1
            _url = data[i]
            i += 1

            if not history:
                continue
            # Data is newest-first in heisse-preise canonical payload.
            price_on_or_before = next(
                (entry for entry in history if entry[0] <= query_day),
                history[0],
            )
            selected_day, selected_price = price_on_or_before
            result.append(
                PriceRecord(
                    store_id=_normalize_store_id(store),
                    product_key=f"{name}_{unit}".lower().replace(" ", "_"),
                    price_eur=selected_price,
                    date=selected_day,
                    source="heisse-preise.io",
                )
            )
        return result

    async def _fetch_store_records(
        self,
        client: httpx.AsyncClient,
        store_key: str,
        day: date,
    ) -> list[PriceRecord]:
        response = await client.get(self.BASE_URL.format(store=store_key))
        response.raise_for_status()
        payload = response.json()
        return self._decompress_records(payload, day)

    async def fetch_daily_prices(self, day: date) -> list[PriceRecord]:
        records: list[PriceRecord] = []
        async with httpx.AsyncClient(timeout=30) as client:
            for store_key in self.store_keys:
                try:
                    records.extend(
                        await self._fetch_store_records(client, store_key, day)
                    )
                except httpx.HTTPError:
                    # Keep provider resilient if one store file is temporarily unavailable.
                    continue
        return records
