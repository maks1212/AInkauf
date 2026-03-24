from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from .providers.austria_price_provider import PriceRecord


def _normalize_text(value: str) -> str:
    return " ".join(
        value.strip().lower().replace("_", " ").replace("-", " ").split()
    )


def _infer_name_from_product_key(product_key: str) -> str:
    tokens = product_key.split("_")
    if len(tokens) > 1 and tokens[-1] in {"g", "kg", "ml", "l", "stk", "pack"}:
        tokens = tokens[:-1]
    return " ".join(tokens).strip().title() or product_key


@dataclass
class MatchResult:
    canonical_product_id: str | None
    confidence: float | None
    reason: str


class ScraperAdminStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._canonical_products: dict[str, dict[str, Any]] = {}
        self._offers: dict[str, dict[str, Any]] = {}
        self._offer_key_index: dict[tuple[str, str, str, str, str], str] = {}
        self._reviews: dict[str, dict[str, Any]] = {}
        self._jobs: list[dict[str, Any]] = []
        self._is_running = False
        self._config: dict[str, Any] = {
            "enabled": False,
            "interval_minutes": 180,
            "max_parallel_stores": 4,
            "retries": 2,
            "updated_at": self._utc_now_iso(),
        }

    @staticmethod
    def _utc_now_iso() -> str:
        return datetime.now(UTC).isoformat()

    # ----------------------------
    # Config
    # ----------------------------
    def get_config(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._config)

    def update_config(
        self,
        *,
        enabled: bool | None = None,
        interval_minutes: int | None = None,
        max_parallel_stores: int | None = None,
        retries: int | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            if enabled is not None:
                self._config["enabled"] = enabled
            if interval_minutes is not None:
                self._config["interval_minutes"] = max(15, interval_minutes)
            if max_parallel_stores is not None:
                self._config["max_parallel_stores"] = max(1, min(max_parallel_stores, 16))
            if retries is not None:
                self._config["retries"] = max(0, min(retries, 5))
            self._config["updated_at"] = self._utc_now_iso()
            return dict(self._config)

    # ----------------------------
    # Canonical catalog CRUD
    # ----------------------------
    def list_canonical_products(self) -> list[dict[str, Any]]:
        with self._lock:
            return sorted(
                [dict(item) for item in self._canonical_products.values()],
                key=lambda item: item["created_at"],
                reverse=True,
            )

    def create_canonical_product(
        self,
        *,
        name: str,
        brand: str | None,
        serial_number: str | None,
        package_quantity: float | None,
        package_unit: str | None,
        category: str | None,
    ) -> dict[str, Any]:
        with self._lock:
            if serial_number:
                serial_norm = serial_number.strip().lower()
                for product in self._canonical_products.values():
                    existing = product.get("serial_number")
                    if existing and existing.strip().lower() == serial_norm:
                        raise ValueError("serial_number already exists.")

            product_id = str(uuid.uuid4())
            row = {
                "id": product_id,
                "name": name.strip(),
                "normalized_name": _normalize_text(name),
                "brand": brand.strip() if brand else None,
                "serial_number": serial_number.strip() if serial_number else None,
                "package_quantity": package_quantity,
                "package_unit": package_unit.strip().lower() if package_unit else None,
                "category": category.strip().lower() if category else None,
                "created_at": self._utc_now_iso(),
                "updated_at": self._utc_now_iso(),
            }
            self._canonical_products[product_id] = row
            return dict(row)

    def update_canonical_product(
        self,
        product_id: str,
        *,
        name: str | None = None,
        brand: str | None = None,
        serial_number: str | None = None,
        package_quantity: float | None = None,
        package_unit: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            row = self._canonical_products.get(product_id)
            if row is None:
                raise KeyError("canonical product not found")
            if serial_number:
                serial_norm = serial_number.strip().lower()
                for existing_id, product in self._canonical_products.items():
                    if existing_id == product_id:
                        continue
                    existing = product.get("serial_number")
                    if existing and existing.strip().lower() == serial_norm:
                        raise ValueError("serial_number already exists.")
                row["serial_number"] = serial_number.strip()
            if name is not None:
                row["name"] = name.strip()
                row["normalized_name"] = _normalize_text(name)
            if brand is not None:
                row["brand"] = brand.strip() if brand else None
            if package_quantity is not None:
                row["package_quantity"] = package_quantity
            if package_unit is not None:
                row["package_unit"] = package_unit.strip().lower() if package_unit else None
            if category is not None:
                row["category"] = category.strip().lower() if category else None
            row["updated_at"] = self._utc_now_iso()
            return dict(row)

    def delete_canonical_product(self, product_id: str) -> None:
        with self._lock:
            if product_id not in self._canonical_products:
                raise KeyError("canonical product not found")
            del self._canonical_products[product_id]
            # keep existing offers as-is; they may later require manual review
            for offer in self._offers.values():
                if offer.get("canonical_product_id") == product_id:
                    offer["canonical_product_id"] = None
                    offer["mapping_confidence"] = None
                    offer["needs_review"] = True
                    offer["review_reason"] = "canonical_product_deleted"
                    self._ensure_review_for_offer(offer)

    # ----------------------------
    # Matching logic
    # ----------------------------
    def _match_product(
        self,
        *,
        source_serial_number: str | None,
        source_product_name: str,
        source_brand: str | None,
        source_package_quantity: float | None,
        source_package_unit: str | None,
    ) -> MatchResult:
        normalized_name = _normalize_text(source_product_name)
        normalized_brand = source_brand.strip().lower() if source_brand else None
        normalized_unit = source_package_unit.strip().lower() if source_package_unit else None

        # 1) strict serial/EAN first (highest confidence).
        if source_serial_number:
            serial_norm = source_serial_number.strip().lower()
            for product in self._canonical_products.values():
                serial = product.get("serial_number")
                if serial and serial.strip().lower() == serial_norm:
                    return MatchResult(
                        canonical_product_id=product["id"],
                        confidence=1.0,
                        reason="serial_number_match",
                    )

        # 2) exact name + brand + quantity/unit.
        for product in self._canonical_products.values():
            same_name = product.get("normalized_name") == normalized_name
            same_brand = (product.get("brand") or "").strip().lower() == (
                normalized_brand or ""
            )
            same_quantity = (
                source_package_quantity is None
                or product.get("package_quantity") is None
                or float(product["package_quantity"]) == float(source_package_quantity)
            )
            same_unit = (
                normalized_unit is None
                or product.get("package_unit") is None
                or (product.get("package_unit") or "").strip().lower() == normalized_unit
            )
            if same_name and same_brand and same_quantity and same_unit:
                return MatchResult(
                    canonical_product_id=product["id"],
                    confidence=0.92,
                    reason="name_brand_size_match",
                )

        # 3) name + size only (ambiguous, still usable if unique).
        candidates: list[dict[str, Any]] = []
        for product in self._canonical_products.values():
            same_name = product.get("normalized_name") == normalized_name
            same_quantity = (
                source_package_quantity is None
                or product.get("package_quantity") is None
                or float(product["package_quantity"]) == float(source_package_quantity)
            )
            same_unit = (
                normalized_unit is None
                or product.get("package_unit") is None
                or (product.get("package_unit") or "").strip().lower() == normalized_unit
            )
            if same_name and same_quantity and same_unit:
                candidates.append(product)

        if len(candidates) == 1:
            return MatchResult(
                canonical_product_id=candidates[0]["id"],
                confidence=0.76,
                reason="name_size_match",
            )
        if len(candidates) > 1:
            return MatchResult(
                canonical_product_id=None,
                confidence=None,
                reason="ambiguous_name_size_match",
            )

        return MatchResult(
            canonical_product_id=None,
            confidence=None,
            reason="no_match",
        )

    # ----------------------------
    # Offers + review queue
    # ----------------------------
    def _ensure_review_for_offer(self, offer: dict[str, Any]) -> None:
        existing = next(
            (
                review
                for review in self._reviews.values()
                if review["scraped_offer_id"] == offer["id"] and review["status"] == "pending"
            ),
            None,
        )
        if existing:
            return
        review_id = str(uuid.uuid4())
        self._reviews[review_id] = {
            "id": review_id,
            "scraped_offer_id": offer["id"],
            "status": "pending",
            "review_reason": offer.get("review_reason"),
            "reviewer_note": None,
            "resolved_canonical_product_id": None,
                "created_at": self._utc_now_iso(),
            "resolved_at": None,
                "updated_at": self._utc_now_iso(),
        }

    def list_offers(
        self,
        *,
        needs_review: bool | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(row) for row in self._offers.values()]
            if needs_review is not None:
                rows = [row for row in rows if row["needs_review"] == needs_review]
            rows.sort(key=lambda row: row["updated_at"], reverse=True)
            return rows[: max(1, min(limit, 2000))]

    def update_offer(
        self,
        offer_id: str,
        *,
        price_eur: float | None = None,
        valid_from: str | None = None,
        valid_to: str | None = None,
        price_type: str | None = None,
        promotion_type: str | None = None,
        promotion_label: str | None = None,
        canonical_product_id: str | None = None,
        needs_review: bool | None = None,
        review_reason: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            row = self._offers.get(offer_id)
            if row is None:
                raise KeyError("offer not found")
            if price_eur is not None:
                row["price_eur"] = price_eur
            if valid_from is not None:
                row["valid_from"] = valid_from
            if valid_to is not None:
                row["valid_to"] = valid_to
            if price_type is not None:
                row["price_type"] = price_type
            if promotion_type is not None:
                row["promotion_type"] = promotion_type
            if promotion_label is not None:
                row["promotion_label"] = promotion_label
            if canonical_product_id is not None:
                if canonical_product_id and canonical_product_id not in self._canonical_products:
                    raise ValueError("canonical_product_id not found")
                row["canonical_product_id"] = canonical_product_id
                if canonical_product_id:
                    row["mapping_confidence"] = 1.0
                    row["needs_review"] = False
                    row["review_reason"] = None
            if needs_review is not None:
                row["needs_review"] = needs_review
            if review_reason is not None:
                row["review_reason"] = review_reason
            row["updated_at"] = self._utc_now_iso()
            if row["needs_review"]:
                self._ensure_review_for_offer(row)
            return dict(row)

    def delete_offer(self, offer_id: str) -> None:
        with self._lock:
            row = self._offers.get(offer_id)
            if row is None:
                raise KeyError("offer not found")
            key = (
                row["source"],
                row["source_store_id"],
                row["source_product_key"],
                row["valid_from"],
                row["price_type"],
            )
            self._offer_key_index.pop(key, None)
            del self._offers[offer_id]
            to_delete = [
                review_id
                for review_id, review in self._reviews.items()
                if review["scraped_offer_id"] == offer_id
            ]
            for review_id in to_delete:
                del self._reviews[review_id]

    def list_reviews(self, *, status: str = "pending", limit: int = 200) -> list[dict[str, Any]]:
        with self._lock:
            rows = [
                dict(row)
                for row in self._reviews.values()
                if status == "all" or row["status"] == status
            ]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            return rows[: max(1, min(limit, 2000))]

    def resolve_review(
        self,
        review_id: str,
        *,
        canonical_product_id: str,
        reviewer_note: str | None,
    ) -> dict[str, Any]:
        with self._lock:
            review = self._reviews.get(review_id)
            if review is None:
                raise KeyError("review not found")
            if canonical_product_id not in self._canonical_products:
                raise ValueError("canonical_product_id not found")
            offer = self._offers.get(review["scraped_offer_id"])
            if offer is None:
                raise KeyError("offer for review not found")

            offer["canonical_product_id"] = canonical_product_id
            offer["mapping_confidence"] = 1.0
            offer["needs_review"] = False
            offer["review_reason"] = None
            offer["updated_at"] = self._utc_now_iso()

            review["status"] = "resolved"
            review["reviewer_note"] = reviewer_note
            review["resolved_canonical_product_id"] = canonical_product_id
            review["resolved_at"] = self._utc_now_iso()
            review["updated_at"] = self._utc_now_iso()
            return dict(review)

    # ----------------------------
    # Scraper ingestion jobs
    # ----------------------------
    def list_jobs(self, limit: int = 40) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(job) for job in self._jobs[: max(1, min(limit, 500))]]

    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    def start_job(self, *, source: str, stores: list[str]) -> dict[str, Any]:
        with self._lock:
            if self._is_running:
                raise RuntimeError("scraper job is already running")
            self._is_running = True
            job = {
                "id": str(uuid.uuid4()),
                "source": source,
                "stores": stores,
                "status": "running",
                "started_at": self._utc_now_iso(),
                "finished_at": None,
                "store_count": len(stores),
                "record_count": 0,
                "inserted_count": 0,
                "matched_count": 0,
                "review_count": 0,
                "error_count": 0,
                "details": {},
            }
            self._jobs.insert(0, job)
            return dict(job)

    def finish_job(
        self,
        job_id: str,
        *,
        status: str,
        record_count: int,
        inserted_count: int,
        matched_count: int,
        review_count: int,
        error_count: int,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            job = next((entry for entry in self._jobs if entry["id"] == job_id), None)
            if job is None:
                raise KeyError("job not found")
            job["status"] = status
            job["finished_at"] = self._utc_now_iso()
            job["record_count"] = record_count
            job["inserted_count"] = inserted_count
            job["matched_count"] = matched_count
            job["review_count"] = review_count
            job["error_count"] = error_count
            job["details"] = details or {}
            self._is_running = False
            return dict(job)

    def ingest_records(
        self,
        *,
        job_id: str,
        records: list[PriceRecord],
        observed_at: datetime | None = None,
    ) -> dict[str, int]:
        with self._lock:
            observed = observed_at or datetime.now(UTC)
            inserted_count = 0
            matched_count = 0
            review_count = 0

            for record in records:
                source_product_name = _infer_name_from_product_key(record.product_key)
                match = self._match_product(
                    source_serial_number=None,
                    source_product_name=source_product_name,
                    source_brand=None,
                    source_package_quantity=record.package_quantity,
                    source_package_unit=record.package_unit,
                )
                needs_review = match.canonical_product_id is None
                valid_from = record.date.isoformat()
                offer_key = (
                    record.source,
                    record.store_id,
                    record.product_key,
                    valid_from,
                    "regular",
                )

                offer_id = self._offer_key_index.get(offer_key)
                if offer_id is None:
                    offer_id = str(uuid.uuid4())
                    self._offer_key_index[offer_key] = offer_id
                    inserted_count += 1

                row = {
                    "id": offer_id,
                    "ingestion_run_id": job_id,
                    "source": record.source,
                    "source_store_id": record.store_id,
                    "source_product_key": record.product_key,
                    "source_serial_number": None,
                    "source_product_name": source_product_name,
                    "source_brand": None,
                    "source_category": None,
                    "source_package_quantity": record.package_quantity,
                    "source_package_unit": record.package_unit,
                    "price_eur": record.price_eur,
                    "currency": "EUR",
                    "price_type": "regular",
                    "valid_from": valid_from,
                    "valid_to": None,
                    "observed_at": observed.isoformat(),
                    "canonical_product_id": match.canonical_product_id,
                    "mapping_confidence": match.confidence,
                    "needs_review": needs_review,
                    "review_reason": match.reason if needs_review else None,
                    "promotion_type": None,
                    "promotion_label": None,
                    "raw_payload": None,
                    "created_at": self._offers.get(offer_id, {}).get(
                        "created_at", self._utc_now_iso()
                    ),
                    "updated_at": self._utc_now_iso(),
                }
                self._offers[offer_id] = row
                if needs_review:
                    review_count += 1
                    self._ensure_review_for_offer(row)
                else:
                    matched_count += 1

            return {
                "record_count": len(records),
                "inserted_count": inserted_count,
                "matched_count": matched_count,
                "review_count": review_count,
            }

