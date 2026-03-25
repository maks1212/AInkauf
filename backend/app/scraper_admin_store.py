from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime
from difflib import SequenceMatcher
from typing import Any

from .providers.austria_price_provider import PriceRecord


def _normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def _normalize_unit(value: str | None) -> str | None:
    if not value:
        return None
    token = value.strip().lower()
    aliases = {
        "gramm": "g",
        "gr": "g",
        "g": "g",
        "kilogramm": "kg",
        "kg": "kg",
        "milliliter": "ml",
        "ml": "ml",
        "liter": "l",
        "l": "l",
        "stk": "stk",
        "stueck": "stk",
        "stuck": "stk",
        "piece": "stk",
        "packung": "pack",
        "pack": "pack",
    }
    return aliases.get(token, token)


def _normalize_quantity(value: float | int | None, unit: str | None) -> tuple[float | None, str | None]:
    if value is None:
        return (None, _normalize_unit(unit))
    normalized_unit = _normalize_unit(unit)
    quantity = float(value)
    if normalized_unit == "kg":
        return (quantity * 1000.0, "g")
    if normalized_unit == "l":
        return (quantity * 1000.0, "ml")
    return (quantity, normalized_unit)


def _text_similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


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
    decision_source: str


class ScraperAdminStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._canonical_products: dict[str, dict[str, Any]] = {}
        self._offers: dict[str, dict[str, Any]] = {}
        self._offer_key_index: dict[tuple[str, str, str, str, str], str] = {}
        self._reviews: dict[str, dict[str, Any]] = {}
        self._events: dict[str, dict[str, Any]] = {}
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
                "package_unit": _normalize_unit(package_unit),
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
                row["package_unit"] = _normalize_unit(package_unit)
            if category is not None:
                row["category"] = category.strip().lower() if category else None
            row["updated_at"] = self._utc_now_iso()
            return dict(row)

    def delete_canonical_product(self, product_id: str) -> None:
        with self._lock:
            if product_id not in self._canonical_products:
                raise KeyError("canonical product not found")
            del self._canonical_products[product_id]
            for offer in self._offers.values():
                if offer.get("canonical_product_id") == product_id:
                    old_offer = dict(offer)
                    offer["canonical_product_id"] = None
                    offer["mapping_confidence"] = None
                    offer["needs_review"] = True
                    offer["review_reason"] = "canonical_product_deleted"
                    offer["decision_source"] = "system"
                    offer["decision_reason"] = "canonical_product_deleted"
                    offer["updated_at"] = self._utc_now_iso()
                    self._ensure_review_for_offer(offer)
                    self._append_event(
                        offer=offer,
                        event_type="REVIEW_REQUIRED",
                        actor_type="system",
                        old_values=old_offer,
                        new_values=offer,
                        decision_reason="canonical_product_deleted",
                        rule_id="catalog.delete",
                        confidence=None,
                        comment="Canonical product removed; manual reassignment required.",
                    )

    # ----------------------------
    # Matching + classification
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
        source_size_qty, source_size_unit = _normalize_quantity(
            source_package_quantity, source_package_unit
        )

        # 1) EAN/serial exact
        if source_serial_number:
            serial_norm = source_serial_number.strip().lower()
            for product in self._canonical_products.values():
                serial = product.get("serial_number")
                if serial and serial.strip().lower() == serial_norm:
                    return MatchResult(product["id"], 1.0, "serial_number_match", "rule")

        # 2) strict deterministic (name + brand + size)
        for product in self._canonical_products.values():
            p_qty, p_unit = _normalize_quantity(
                product.get("package_quantity"), product.get("package_unit")
            )
            same_name = product.get("normalized_name") == normalized_name
            same_brand = (product.get("brand") or "").strip().lower() == (
                normalized_brand or ""
            )
            same_size = (
                source_size_qty is None
                or p_qty is None
                or (abs(float(p_qty) - float(source_size_qty)) < 1e-6 and p_unit == source_size_unit)
            )
            if same_name and same_brand and same_size:
                return MatchResult(product["id"], 0.95, "name_brand_size_match", "rule")

        # 3) NLP/fuzzy (name similarity + soft brand/size bonus)
        scored: list[tuple[float, dict[str, Any]]] = []
        for product in self._canonical_products.values():
            base = _text_similarity(normalized_name, product.get("normalized_name", ""))
            if base < 0.70:
                continue
            score = base
            product_brand = (product.get("brand") or "").strip().lower()
            if normalized_brand and product_brand:
                if normalized_brand == product_brand:
                    score += 0.08
                elif normalized_brand in product_brand or product_brand in normalized_brand:
                    score += 0.04
            p_qty, p_unit = _normalize_quantity(
                product.get("package_quantity"), product.get("package_unit")
            )
            if (
                source_size_qty is not None
                and p_qty is not None
                and source_size_unit is not None
                and p_unit is not None
                and source_size_unit == p_unit
            ):
                rel_delta = abs(float(source_size_qty) - float(p_qty)) / max(float(source_size_qty), 1.0)
                if rel_delta <= 0.05:
                    score += 0.05
                elif rel_delta <= 0.20:
                    score += 0.02
            scored.append((score, product))

        if scored:
            scored.sort(key=lambda x: x[0], reverse=True)
            best_score, best_product = scored[0]
            second_score = scored[1][0] if len(scored) > 1 else 0.0
            if best_score >= 0.90 and (best_score - second_score) >= 0.05:
                return MatchResult(
                    best_product["id"],
                    round(best_score, 4),
                    "nlp_fuzzy_high_confidence",
                    "nlp",
                )
            if best_score >= 0.80 and (best_score - second_score) >= 0.10:
                return MatchResult(
                    best_product["id"],
                    round(best_score, 4),
                    "nlp_fuzzy_medium_confidence",
                    "nlp",
                )
            return MatchResult(
                None,
                round(best_score, 4),
                "ambiguous_nlp_match",
                "nlp",
            )

        return MatchResult(None, None, "no_match", "rule")

    def _find_latest_offer_for_same_listing(
        self, *, source: str, source_store_id: str, source_product_key: str, exclude_offer_id: str | None
    ) -> dict[str, Any] | None:
        candidates = [
            offer
            for offer in self._offers.values()
            if offer["source"] == source
            and offer["source_store_id"] == source_store_id
            and offer["source_product_key"] == source_product_key
            and offer["id"] != exclude_offer_id
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item["valid_from"], item["updated_at"]), reverse=True)
        return candidates[0]

    def _classify_change(
        self,
        *,
        existing_offer: dict[str, Any] | None,
        latest_listing_offer: dict[str, Any] | None,
        price_type: str,
        price_eur: float,
    ) -> str:
        if existing_offer is None:
            if latest_listing_offer is None:
                return "NEW_LISTING"
            if price_type == "promo":
                return "PROMO_START"
            previous_price = float(latest_listing_offer.get("price_eur", 0))
            if previous_price and price_eur > previous_price:
                return "PRICE_CHANGE_UP"
            if previous_price and price_eur < previous_price:
                return "PRICE_CHANGE_DOWN"
            return "NO_MATERIAL_CHANGE"

        previous_price = float(existing_offer.get("price_eur", 0))
        previous_type = existing_offer.get("price_type", "regular")
        if previous_type != "promo" and price_type == "promo":
            return "PROMO_START"
        if previous_type == "promo" and price_type != "promo":
            return "PROMO_END"
        if previous_type == "promo" and price_type == "promo" and price_eur != previous_price:
            return "PROMO_UPDATE"
        if price_eur > previous_price:
            return "PRICE_CHANGE_UP"
        if price_eur < previous_price:
            return "PRICE_CHANGE_DOWN"
        return "NO_MATERIAL_CHANGE"

    # ----------------------------
    # Events/history
    # ----------------------------
    def _append_event(
        self,
        *,
        offer: dict[str, Any],
        event_type: str,
        actor_type: str,
        old_values: dict[str, Any] | None,
        new_values: dict[str, Any] | None,
        decision_reason: str | None,
        rule_id: str | None,
        confidence: float | None,
        comment: str | None = None,
        actor_id: str | None = None,
    ) -> dict[str, Any]:
        event_id = str(uuid.uuid4())
        row = {
            "id": event_id,
            "scraped_offer_id": offer["id"],
            "ingestion_run_id": offer.get("ingestion_run_id"),
            "event_type": event_type,
            "actor_type": actor_type,
            "actor_id": actor_id,
            "old_values": old_values,
            "new_values": new_values,
            "decision_reason": decision_reason,
            "rule_id": rule_id,
            "confidence": confidence,
            "comment": comment,
            "created_at": self._utc_now_iso(),
        }
        self._events[event_id] = row
        return dict(row)

    def list_offer_events(
        self,
        *,
        offer_id: str | None = None,
        event_type: str | None = None,
        actor_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with self._lock:
            rows = [dict(row) for row in self._events.values()]
            if offer_id:
                rows = [row for row in rows if row["scraped_offer_id"] == offer_id]
            if event_type:
                rows = [row for row in rows if row["event_type"] == event_type]
            if actor_type:
                rows = [row for row in rows if row.get("actor_type") == actor_type]
            rows.sort(key=lambda row: row["created_at"], reverse=True)
            bounded_offset = max(0, offset)
            bounded_limit = max(1, min(limit, 2000))
            return rows[bounded_offset : bounded_offset + bounded_limit]

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

    def list_offers(self, *, needs_review: bool | None = None, limit: int = 200) -> list[dict[str, Any]]:
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
            old_row = dict(row)
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
                    row["decision_source"] = "reviewer"
                    row["decision_reason"] = "manual_canonical_assignment"
            if needs_review is not None:
                row["needs_review"] = needs_review
            if review_reason is not None:
                row["review_reason"] = review_reason
            row["updated_at"] = self._utc_now_iso()
            if row["needs_review"]:
                self._ensure_review_for_offer(row)
            self._append_event(
                offer=row,
                event_type="OFFER_UPDATED",
                actor_type="reviewer",
                old_values=old_row,
                new_values=dict(row),
                decision_reason=row.get("decision_reason"),
                rule_id="api.offer.update",
                confidence=row.get("mapping_confidence"),
                comment="Offer manually updated via admin endpoint.",
            )
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
            self._append_event(
                offer=row,
                event_type="OFFER_DELETED",
                actor_type="reviewer",
                old_values=row,
                new_values=None,
                decision_reason="manual_delete",
                rule_id="api.offer.delete",
                confidence=None,
                comment="Offer deleted via admin endpoint.",
            )

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
            old_offer = dict(offer)
            old_review = dict(review)

            offer["canonical_product_id"] = canonical_product_id
            offer["mapping_confidence"] = 1.0
            offer["needs_review"] = False
            offer["review_reason"] = None
            offer["decision_source"] = "reviewer"
            offer["decision_reason"] = "manual_review_resolution"
            offer["updated_at"] = self._utc_now_iso()

            review["status"] = "resolved"
            review["reviewer_note"] = reviewer_note
            review["resolved_canonical_product_id"] = canonical_product_id
            review["resolved_at"] = self._utc_now_iso()
            review["updated_at"] = self._utc_now_iso()

            self._append_event(
                offer=offer,
                event_type="REVIEW_RESOLVED",
                actor_type="reviewer",
                old_values={"offer": old_offer, "review": old_review},
                new_values={"offer": dict(offer), "review": dict(review)},
                decision_reason="manual_review_resolution",
                rule_id="review.resolve",
                confidence=1.0,
                comment=reviewer_note,
            )
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
            auto_resolved_count = 0
            classified_counts: dict[str, int] = {}

            for record in records:
                source_product_name = _infer_name_from_product_key(record.product_key)
                match = self._match_product(
                    source_serial_number=None,
                    source_product_name=source_product_name,
                    source_brand=None,
                    source_package_quantity=record.package_quantity,
                    source_package_unit=record.package_unit,
                )
                confidence = float(match.confidence) if match.confidence is not None else None
                auto_accept_threshold = 0.90
                needs_review = not (
                    match.canonical_product_id is not None
                    and confidence is not None
                    and confidence >= auto_accept_threshold
                )
                valid_from = record.date.isoformat()
                offer_key = (
                    record.source,
                    record.store_id,
                    record.product_key,
                    valid_from,
                    "regular",
                )
                offer_id = self._offer_key_index.get(offer_key)
                existing_offer = self._offers.get(offer_id) if offer_id else None
                latest_listing_offer = self._find_latest_offer_for_same_listing(
                    source=record.source,
                    source_store_id=record.store_id,
                    source_product_key=record.product_key,
                    exclude_offer_id=offer_id,
                )

                if offer_id is None:
                    offer_id = str(uuid.uuid4())
                    self._offer_key_index[offer_key] = offer_id
                    inserted_count += 1

                price_type = "regular"
                change_type = self._classify_change(
                    existing_offer=existing_offer,
                    latest_listing_offer=latest_listing_offer,
                    price_type=price_type,
                    price_eur=record.price_eur,
                )
                classified_counts[change_type] = classified_counts.get(change_type, 0) + 1

                old_row = dict(existing_offer) if existing_offer else None
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
                    "source_package_unit": _normalize_unit(record.package_unit),
                    "price_eur": record.price_eur,
                    "currency": "EUR",
                    "price_type": price_type,
                    "valid_from": valid_from,
                    "valid_to": None,
                    "observed_at": observed.isoformat(),
                    "canonical_product_id": match.canonical_product_id if not needs_review else None,
                    "mapping_confidence": confidence if not needs_review else confidence,
                    "needs_review": needs_review,
                    "review_reason": match.reason if needs_review else None,
                    "promotion_type": None,
                    "promotion_label": None,
                    "change_type": change_type,
                    "decision_source": "nlp" if match.decision_source == "nlp" else "rule",
                    "decision_reason": match.reason,
                    "raw_payload": None,
                    "created_at": self._offers.get(offer_id, {}).get("created_at", self._utc_now_iso()),
                    "updated_at": self._utc_now_iso(),
                }
                self._offers[offer_id] = row

                if needs_review:
                    review_count += 1
                    self._ensure_review_for_offer(row)
                    self._append_event(
                        offer=row,
                        event_type="REVIEW_REQUIRED",
                        actor_type="system",
                        old_values=old_row,
                        new_values=dict(row),
                        decision_reason=match.reason,
                        rule_id=f"match.{match.reason}",
                        confidence=confidence,
                        comment=f"auto_match_failed:{match.decision_source}",
                    )
                else:
                    matched_count += 1
                    auto_resolved_count += 1
                    self._append_event(
                        offer=row,
                        event_type="MATCHED_AUTO",
                        actor_type="system",
                        old_values=old_row,
                        new_values=dict(row),
                        decision_reason=match.reason,
                        rule_id=f"match.{match.reason}",
                        confidence=confidence,
                        comment=f"auto_match_success:{match.decision_source}",
                    )

                self._append_event(
                    offer=row,
                    event_type=change_type,
                    actor_type="system",
                    old_values=old_row,
                    new_values=dict(row),
                    decision_reason=row.get("decision_reason"),
                    rule_id=f"classify.{change_type.lower()}",
                    confidence=confidence,
                    comment="change_type_classification",
                )

            return {
                "record_count": len(records),
                "inserted_count": inserted_count,
                "matched_count": matched_count,
                "review_count": review_count,
                "auto_resolved_count": auto_resolved_count,
                "classified_counts": classified_counts,
            }

