from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class ChainRecord:
    code: str
    display_name: str
    tier: int


@dataclass(frozen=True)
class StoreRecord:
    store_id: str
    chain: str
    name: str
    lat: float
    lng: float
    address: str


@dataclass(frozen=True)
class PriceObservationRecord:
    store_id: str
    product_key: str
    product_name: str
    brand: str | None
    category: str
    package_quantity: float
    package_unit: str
    price_eur: float
    price_type: str  # regular | promo
    valid_from: date
    valid_to: date | None
    source: str
    promotion_type: str | None = None
    promotion_label: str | None = None


@dataclass(frozen=True)
class BasketItemRequest:
    product_key: str
    quantity: float
    unit: str


def _normalize_unit(unit: str) -> str:
    normalized = unit.strip().lower()
    if normalized in {"stueck", "stuck"}:
        return "stk"
    if normalized == "paket":
        return "pack"
    return normalized


def _to_base_quantity(quantity: float, unit: str) -> tuple[str, float]:
    normalized = _normalize_unit(unit)
    if normalized == "g":
        return ("mass", quantity / 1000.0)
    if normalized == "kg":
        return ("mass", quantity)
    if normalized == "ml":
        return ("volume", quantity / 1000.0)
    if normalized == "l":
        return ("volume", quantity)
    if normalized in {"stk", "pack"}:
        return ("count", quantity)
    return ("unknown", quantity)


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_km = 6371.0
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


class PricePlatformReadModel:
    """Read-model style in-memory seed for the price-platform API."""

    def __init__(self) -> None:
        today = date.today()
        self._chains: list[ChainRecord] = [
            ChainRecord(code="billa", display_name="BILLA", tier=1),
            ChainRecord(code="spar", display_name="SPAR", tier=1),
            ChainRecord(code="hofer", display_name="HOFER", tier=1),
            ChainRecord(code="lidl", display_name="LIDL", tier=1),
            ChainRecord(code="penny", display_name="PENNY", tier=1),
            ChainRecord(code="mpreis", display_name="MPREIS", tier=1),
            ChainRecord(code="unimarkt", display_name="UNIMARKT", tier=2),
            ChainRecord(code="nahfrisch", display_name="Nah&Frisch", tier=2),
            ChainRecord(code="adeg", display_name="ADEG", tier=2),
        ]

        self._stores: list[StoreRecord] = [
            StoreRecord(
                store_id="store-billa-1010",
                chain="billa",
                name="BILLA Wien Innere Stadt",
                lat=48.2102,
                lng=16.3700,
                address="Rotenturmstrasse 22, 1010 Wien",
            ),
            StoreRecord(
                store_id="store-spar-1020",
                chain="spar",
                name="SPAR Wien Leopoldstadt",
                lat=48.2190,
                lng=16.3890,
                address="Praterstrasse 44, 1020 Wien",
            ),
            StoreRecord(
                store_id="store-hofer-1150",
                chain="hofer",
                name="HOFER Wien Rudolfsheim",
                lat=48.1940,
                lng=16.3300,
                address="Hutteldorfer Strasse 58, 1150 Wien",
            ),
            StoreRecord(
                store_id="store-lidl-1100",
                chain="lidl",
                name="LIDL Wien Favoriten",
                lat=48.1710,
                lng=16.3760,
                address="Laxenburger Strasse 18, 1100 Wien",
            ),
            StoreRecord(
                store_id="store-penny-1200",
                chain="penny",
                name="PENNY Wien Brigittenau",
                lat=48.2385,
                lng=16.3730,
                address="Jagerstrasse 43, 1200 Wien",
            ),
            StoreRecord(
                store_id="store-mpreis-6020",
                chain="mpreis",
                name="MPREIS Innsbruck Zentrum",
                lat=47.2680,
                lng=11.3920,
                address="Maria-Theresien-Strasse 18, 6020 Innsbruck",
            ),
        ]

        self._prices: list[PriceObservationRecord] = [
            PriceObservationRecord(
                store_id="store-billa-1010",
                product_key="gouda",
                product_name="Gouda",
                brand="Clever",
                category="kaese",
                package_quantity=250,
                package_unit="g",
                price_eur=2.49,
                price_type="regular",
                valid_from=today - timedelta(days=10),
                valid_to=None,
                source="scrape:billa",
            ),
            PriceObservationRecord(
                store_id="store-spar-1020",
                product_key="gouda",
                product_name="Gouda",
                brand="S-Budget",
                category="kaese",
                package_quantity=250,
                package_unit="g",
                price_eur=2.39,
                price_type="regular",
                valid_from=today - timedelta(days=8),
                valid_to=None,
                source="scrape:spar",
            ),
            PriceObservationRecord(
                store_id="store-hofer-1150",
                product_key="gouda",
                product_name="Gouda",
                brand="Milfina",
                category="kaese",
                package_quantity=250,
                package_unit="g",
                price_eur=1.99,
                price_type="regular",
                valid_from=today - timedelta(days=7),
                valid_to=None,
                source="scrape:hofer",
            ),
            PriceObservationRecord(
                store_id="store-billa-1010",
                product_key="pizza_margherita",
                product_name="Pizza Margherita",
                brand="Billa",
                category="tk",
                package_quantity=1,
                package_unit="stk",
                price_eur=3.29,
                price_type="regular",
                valid_from=today - timedelta(days=20),
                valid_to=None,
                source="scrape:billa",
            ),
            PriceObservationRecord(
                store_id="store-billa-1010",
                product_key="pizza_margherita",
                product_name="Pizza Margherita",
                brand="Billa",
                category="tk",
                package_quantity=1,
                package_unit="stk",
                price_eur=2.49,
                price_type="promo",
                valid_from=today - timedelta(days=1),
                valid_to=today + timedelta(days=6),
                source="scrape:billa",
                promotion_type="percent",
                promotion_label="-24% Wochenaktion",
            ),
            PriceObservationRecord(
                store_id="store-spar-1020",
                product_key="pizza_margherita",
                product_name="Pizza Margherita",
                brand="Spar",
                category="tk",
                package_quantity=1,
                package_unit="stk",
                price_eur=2.79,
                price_type="regular",
                valid_from=today - timedelta(days=15),
                valid_to=None,
                source="scrape:spar",
            ),
            PriceObservationRecord(
                store_id="store-hofer-1150",
                product_key="pizza_margherita",
                product_name="Pizza Margherita",
                brand="Gustavo",
                category="tk",
                package_quantity=1,
                package_unit="stk",
                price_eur=2.39,
                price_type="regular",
                valid_from=today - timedelta(days=9),
                valid_to=None,
                source="scrape:hofer",
            ),
            PriceObservationRecord(
                store_id="store-billa-1010",
                product_key="milch_1l",
                product_name="Milch 1L",
                brand="Clever",
                category="milchprodukte",
                package_quantity=1,
                package_unit="l",
                price_eur=1.29,
                price_type="regular",
                valid_from=today - timedelta(days=5),
                valid_to=None,
                source="scrape:billa",
            ),
            PriceObservationRecord(
                store_id="store-spar-1020",
                product_key="milch_1l",
                product_name="Milch 1L",
                brand="S-Budget",
                category="milchprodukte",
                package_quantity=1,
                package_unit="l",
                price_eur=1.19,
                price_type="regular",
                valid_from=today - timedelta(days=5),
                valid_to=None,
                source="scrape:spar",
            ),
            PriceObservationRecord(
                store_id="store-hofer-1150",
                product_key="milch_1l",
                product_name="Milch 1L",
                brand="Milfina",
                category="milchprodukte",
                package_quantity=1,
                package_unit="l",
                price_eur=1.09,
                price_type="regular",
                valid_from=today - timedelta(days=5),
                valid_to=None,
                source="scrape:hofer",
            ),
        ]

    def list_chains(self) -> list[ChainRecord]:
        return sorted(self._chains, key=lambda entry: (entry.tier, entry.display_name))

    def list_stores(
        self,
        chain: str | None = None,
        lat: float | None = None,
        lng: float | None = None,
        radius_km: float | None = None,
    ) -> list[tuple[StoreRecord, float | None]]:
        filtered = self._stores
        if chain:
            chain_key = chain.strip().lower()
            filtered = [entry for entry in filtered if entry.chain == chain_key]

        rows: list[tuple[StoreRecord, float | None]] = []
        for store in filtered:
            distance = None
            if lat is not None and lng is not None:
                distance = _haversine_km(lat, lng, store.lat, store.lng)
                if radius_km is not None and distance > radius_km:
                    continue
            rows.append((store, distance))

        return sorted(rows, key=lambda entry: (entry[1] is None, entry[1] or 0.0, entry[0].name))

    def _is_active(self, record: PriceObservationRecord, on_date: date) -> bool:
        if record.valid_from > on_date:
            return False
        if record.valid_to is not None and on_date > record.valid_to:
            return False
        return True

    def get_current_price(
        self,
        store_id: str,
        product_key: str,
        on_date: date | None = None,
    ) -> PriceObservationRecord | None:
        lookup_date = on_date or date.today()
        candidates = [
            record
            for record in self._prices
            if record.store_id == store_id
            and record.product_key == product_key
            and self._is_active(record, lookup_date)
        ]
        if not candidates:
            return None

        def _sort_key(record: PriceObservationRecord) -> tuple[int, date]:
            promo_priority = 0 if record.price_type == "promo" else 1
            return (promo_priority, record.valid_from)

        candidates.sort(key=_sort_key, reverse=True)
        return candidates[0]

    def get_price_history(
        self,
        store_id: str,
        product_key: str,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[PriceObservationRecord]:
        history = [
            record
            for record in self._prices
            if record.store_id == store_id and record.product_key == product_key
        ]
        if from_date is not None:
            history = [
                record
                for record in history
                if (record.valid_to is None or record.valid_to >= from_date)
            ]
        if to_date is not None:
            history = [record for record in history if record.valid_from <= to_date]
        return sorted(history, key=lambda record: record.valid_from)

    def get_current_promotions(
        self,
        chain: str | None = None,
        store_id: str | None = None,
        on_date: date | None = None,
    ) -> list[PriceObservationRecord]:
        lookup_date = on_date or date.today()
        selected_stores = {
            record.store_id
            for record in self._stores
            if chain is None or record.chain == chain.strip().lower()
        }
        if store_id:
            selected_stores = {store_id}

        return [
            record
            for record in self._prices
            if record.store_id in selected_stores
            and record.price_type == "promo"
            and self._is_active(record, lookup_date)
        ]

    def quote_basket(
        self,
        items: list[BasketItemRequest],
        store_ids: list[str] | None = None,
        on_date: date | None = None,
    ) -> list[dict]:
        lookup_date = on_date or date.today()
        stores = self._stores
        if store_ids:
            allowed = set(store_ids)
            stores = [store for store in stores if store.store_id in allowed]

        quotes: list[dict] = []
        for store in stores:
            line_items: list[dict] = []
            subtotal = 0.0
            missing_items = 0
            for item in items:
                record = self.get_current_price(
                    store_id=store.store_id,
                    product_key=item.product_key,
                    on_date=lookup_date,
                )
                if record is None:
                    missing_items += 1
                    line_items.append(
                        {
                            "product_key": item.product_key,
                            "requested_quantity": item.quantity,
                            "requested_unit": _normalize_unit(item.unit),
                            "found": False,
                            "reason": "no_current_price",
                        }
                    )
                    continue

                req_family, req_qty = _to_base_quantity(item.quantity, item.unit)
                pkg_family, pkg_qty = _to_base_quantity(
                    record.package_quantity,
                    record.package_unit,
                )
                if req_family != pkg_family:
                    missing_items += 1
                    line_items.append(
                        {
                            "product_key": item.product_key,
                            "requested_quantity": item.quantity,
                            "requested_unit": _normalize_unit(item.unit),
                            "found": False,
                            "reason": "unit_family_mismatch",
                        }
                    )
                    continue

                ratio = req_qty / max(pkg_qty, 0.0001)
                package_count = max(1, math.ceil(ratio))
                line_total = package_count * record.price_eur
                subtotal += line_total
                line_items.append(
                    {
                        "product_key": item.product_key,
                        "product_name": record.product_name,
                        "brand": record.brand,
                        "requested_quantity": item.quantity,
                        "requested_unit": _normalize_unit(item.unit),
                        "package_quantity": record.package_quantity,
                        "package_unit": record.package_unit,
                        "package_count": package_count,
                        "unit_price_eur": record.price_eur,
                        "line_total_eur": round(line_total, 2),
                        "valid_from": record.valid_from.isoformat(),
                        "valid_to": record.valid_to.isoformat()
                        if record.valid_to
                        else None,
                        "price_type": record.price_type,
                        "found": True,
                    }
                )

            quotes.append(
                {
                    "store_id": store.store_id,
                    "chain": store.chain,
                    "store_name": store.name,
                    "missing_items": missing_items,
                    "subtotal_eur": round(subtotal, 2),
                    "line_items": line_items,
                }
            )

        return sorted(quotes, key=lambda row: (row["missing_items"], row["subtotal_eur"]))
