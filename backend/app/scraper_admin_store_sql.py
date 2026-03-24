from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from .database import Base, SessionLocal, engine
from .providers.austria_price_provider import PriceRecord
from .scraper_admin_models import (
    CanonicalProductCatalog,
    ScrapedOffer,
    ScrapedOfferReview,
    ScraperChain,
    ScraperJobRun,
)
from .scraper_admin_store import ScraperAdminStore


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ScraperAdminSqlStore(ScraperAdminStore):
    """
    SQL-backed store that preserves the in-memory store interface.
    Config and minimal scheduler state stay in-process for now;
    catalog/offers/reviews/jobs are persisted.
    """

    def create_schema(self) -> None:
        Base.metadata.create_all(bind=engine)

    def _row_to_product(self, row: CanonicalProductCatalog) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "name": row.name,
            "normalized_name": row.normalized_name,
            "brand": row.brand,
            "serial_number": row.serial_number,
            "package_quantity": float(row.package_quantity)
            if row.package_quantity is not None
            else None,
            "package_unit": row.package_unit,
            "category": row.category,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _row_to_offer(self, row: ScrapedOffer) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "ingestion_run_id": str(row.ingestion_run_id) if row.ingestion_run_id else None,
            "source": row.source,
            "source_store_id": row.source_store_id,
            "source_product_key": row.source_product_key,
            "source_serial_number": row.source_serial_number,
            "source_product_name": row.source_product_name,
            "source_brand": row.source_brand,
            "source_category": row.source_category,
            "source_package_quantity": float(row.source_package_quantity)
            if row.source_package_quantity is not None
            else None,
            "source_package_unit": row.source_package_unit,
            "price_eur": float(row.price_eur),
            "currency": row.currency,
            "price_type": row.price_type,
            "valid_from": row.valid_from.isoformat(),
            "valid_to": row.valid_to.isoformat() if row.valid_to else None,
            "observed_at": row.observed_at.isoformat(),
            "canonical_product_id": str(row.canonical_product_id)
            if row.canonical_product_id
            else None,
            "mapping_confidence": float(row.mapping_confidence)
            if row.mapping_confidence is not None
            else None,
            "needs_review": row.needs_review,
            "review_reason": row.review_reason,
            "promotion_type": row.promotion_type,
            "promotion_label": row.promotion_label,
            "raw_payload": row.raw_payload,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _row_to_review(self, row: ScrapedOfferReview) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "scraped_offer_id": str(row.scraped_offer_id),
            "status": row.status,
            "review_reason": None,
            "reviewer_note": row.reviewer_note,
            "resolved_canonical_product_id": str(row.resolved_canonical_product_id)
            if row.resolved_canonical_product_id
            else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "resolved_at": row.resolved_at.isoformat() if row.resolved_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }

    def _row_to_job(self, row: ScraperJobRun) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "source": row.source,
            "status": row.status,
            "stores": (row.details or {}).get("stores", []),
            "started_at": row.started_at.isoformat(),
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "store_count": row.store_count,
            "record_count": row.record_count,
            "inserted_count": row.inserted_count,
            "matched_count": row.matched_count,
            "review_count": row.review_count,
            "error_count": row.error_count,
            "details": row.details or {},
        }

    def list_canonical_products(self) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(CanonicalProductCatalog).order_by(CanonicalProductCatalog.created_at.desc())
            ).all()
            return [self._row_to_product(row) for row in rows]

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
        normalized_name = " ".join(
            name.strip().lower().replace("_", " ").replace("-", " ").split()
        )
        with SessionLocal() as session:
            row = CanonicalProductCatalog(
                id=uuid.uuid4(),
                serial_number=serial_number.strip() if serial_number else None,
                name=name.strip(),
                normalized_name=normalized_name,
                brand=brand.strip() if brand else None,
                category=category.strip().lower() if category else None,
                package_quantity=package_quantity,
                package_unit=package_unit.strip().lower() if package_unit else None,
                created_at=_utc_now(),
                updated_at=_utc_now(),
            )
            session.add(row)
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("serial_number already exists.") from exc
            session.refresh(row)
            return self._row_to_product(row)

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
        with SessionLocal() as session:
            row = session.get(CanonicalProductCatalog, uuid.UUID(product_id))
            if row is None:
                raise KeyError("canonical product not found")
            if name is not None:
                row.name = name.strip()
                row.normalized_name = " ".join(
                    name.strip().lower().replace("_", " ").replace("-", " ").split()
                )
            if brand is not None:
                row.brand = brand.strip() if brand else None
            if serial_number is not None:
                row.serial_number = serial_number.strip() if serial_number else None
            if package_quantity is not None:
                row.package_quantity = package_quantity
            if package_unit is not None:
                row.package_unit = package_unit.strip().lower() if package_unit else None
            if category is not None:
                row.category = category.strip().lower() if category else None
            row.updated_at = _utc_now()
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("serial_number already exists.") from exc
            session.refresh(row)
            return self._row_to_product(row)

    def delete_canonical_product(self, product_id: str) -> None:
        with SessionLocal() as session:
            row = session.get(CanonicalProductCatalog, uuid.UUID(product_id))
            if row is None:
                raise KeyError("canonical product not found")
            session.delete(row)
            session.commit()

    def list_offers(
        self,
        *,
        needs_review: bool | None = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            stmt = select(ScrapedOffer).order_by(ScrapedOffer.updated_at.desc())
            if needs_review is not None:
                stmt = stmt.where(ScrapedOffer.needs_review.is_(needs_review))
            rows = session.scalars(stmt.limit(max(1, min(limit, 2000)))).all()
            return [self._row_to_offer(row) for row in rows]

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
        with SessionLocal() as session:
            row = session.get(ScrapedOffer, uuid.UUID(offer_id))
            if row is None:
                raise KeyError("offer not found")
            if price_eur is not None:
                row.price_eur = price_eur
            if valid_from is not None:
                row.valid_from = datetime.fromisoformat(valid_from).date()
            if valid_to is not None:
                row.valid_to = datetime.fromisoformat(valid_to).date() if valid_to else None
            if price_type is not None:
                row.price_type = price_type
            if promotion_type is not None:
                row.promotion_type = promotion_type
            if promotion_label is not None:
                row.promotion_label = promotion_label
            if canonical_product_id is not None:
                row.canonical_product_id = (
                    uuid.UUID(canonical_product_id) if canonical_product_id else None
                )
                if canonical_product_id:
                    row.mapping_confidence = 1.0
                    row.needs_review = False
                    row.review_reason = None
            if needs_review is not None:
                row.needs_review = needs_review
            if review_reason is not None:
                row.review_reason = review_reason
            row.updated_at = _utc_now()
            session.commit()
            session.refresh(row)
            return self._row_to_offer(row)

    def delete_offer(self, offer_id: str) -> None:
        with SessionLocal() as session:
            row = session.get(ScrapedOffer, uuid.UUID(offer_id))
            if row is None:
                raise KeyError("offer not found")
            session.delete(row)
            session.commit()

    def list_reviews(self, *, status: str = "pending", limit: int = 200) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            stmt = select(ScrapedOfferReview).order_by(ScrapedOfferReview.created_at.desc())
            if status != "all":
                stmt = stmt.where(ScrapedOfferReview.status == status)
            rows = session.scalars(stmt.limit(max(1, min(limit, 2000)))).all()
            return [self._row_to_review(row) for row in rows]

    def resolve_review(
        self,
        review_id: str,
        *,
        canonical_product_id: str,
        reviewer_note: str | None,
    ) -> dict[str, Any]:
        with SessionLocal() as session:
            review = session.get(ScrapedOfferReview, uuid.UUID(review_id))
            if review is None:
                raise KeyError("review not found")
            offer = session.get(ScrapedOffer, review.scraped_offer_id)
            if offer is None:
                raise KeyError("offer for review not found")
            canonical_uuid = uuid.UUID(canonical_product_id)
            canonical = session.get(CanonicalProductCatalog, canonical_uuid)
            if canonical is None:
                raise ValueError("canonical_product_id not found")

            offer.canonical_product_id = canonical_uuid
            offer.mapping_confidence = 1.0
            offer.needs_review = False
            offer.review_reason = None
            offer.updated_at = _utc_now()

            review.status = "resolved"
            review.reviewer_note = reviewer_note
            review.resolved_canonical_product_id = canonical_uuid
            review.resolved_at = _utc_now()
            review.updated_at = _utc_now()

            session.commit()
            session.refresh(review)
            return self._row_to_review(review)

    def list_jobs(self, limit: int = 40) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            rows = session.scalars(
                select(ScraperJobRun).order_by(ScraperJobRun.started_at.desc()).limit(max(1, min(limit, 500)))
            ).all()
            return [self._row_to_job(row) for row in rows]

    def is_running(self) -> bool:
        with SessionLocal() as session:
            active = session.scalars(
                select(ScraperJobRun).where(ScraperJobRun.status == "running").limit(1)
            ).first()
            return active is not None

    def start_job(self, *, source: str, stores: list[str]) -> dict[str, Any]:
        with SessionLocal() as session:
            active = session.scalars(
                select(ScraperJobRun).where(ScraperJobRun.status == "running").limit(1)
            ).first()
            if active is not None:
                raise RuntimeError("scraper job is already running")

            row = ScraperJobRun(
                id=uuid.uuid4(),
                source=source,
                started_at=_utc_now(),
                status="running",
                store_count=len(stores),
                record_count=0,
                inserted_count=0,
                matched_count=0,
                review_count=0,
                error_count=0,
                details={"stores": stores},
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            return self._row_to_job(row)

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
        with SessionLocal() as session:
            row = session.get(ScraperJobRun, uuid.UUID(job_id))
            if row is None:
                raise KeyError("job not found")
            row.status = status
            row.finished_at = _utc_now()
            row.record_count = record_count
            row.inserted_count = inserted_count
            row.matched_count = matched_count
            row.review_count = review_count
            row.error_count = error_count
            row.details = details or {}
            session.commit()
            session.refresh(row)
            return self._row_to_job(row)

    def ingest_records(
        self,
        *,
        job_id: str,
        records: list[PriceRecord],
        observed_at: datetime | None = None,
    ) -> dict[str, int]:
        # Reuse matching and decision logic from parent in-memory structure,
        # then persist rows into SQL store for now.
        # This keeps behavior aligned while we incrementally move matching to SQL queries.
        stats = super().ingest_records(
            job_id=job_id,
            records=records,
            observed_at=observed_at,
        )
        with SessionLocal() as session:
            # Persist canonical products currently held in-memory cache.
            for product in self._canonical_products.values():
                product_uuid = uuid.UUID(product["id"])
                exists = session.get(CanonicalProductCatalog, product_uuid)
                if exists:
                    continue
                session.add(
                    CanonicalProductCatalog(
                        id=product_uuid,
                        serial_number=product.get("serial_number"),
                        name=product["name"],
                        normalized_name=product["normalized_name"],
                        brand=product.get("brand"),
                        category=product.get("category"),
                        package_quantity=product.get("package_quantity"),
                        package_unit=product.get("package_unit"),
                        created_at=datetime.fromisoformat(product["created_at"]),
                        updated_at=datetime.fromisoformat(product["updated_at"]),
                    )
                )

            for offer in self._offers.values():
                offer_uuid = uuid.UUID(offer["id"])
                exists = session.get(ScrapedOffer, offer_uuid)
                if exists:
                    exists.price_eur = offer["price_eur"]
                    exists.valid_from = datetime.fromisoformat(offer["valid_from"]).date()
                    exists.valid_to = (
                        datetime.fromisoformat(offer["valid_to"]).date()
                        if offer["valid_to"]
                        else None
                    )
                    exists.canonical_product_id = (
                        uuid.UUID(offer["canonical_product_id"])
                        if offer["canonical_product_id"]
                        else None
                    )
                    exists.mapping_confidence = offer["mapping_confidence"]
                    exists.needs_review = offer["needs_review"]
                    exists.review_reason = offer["review_reason"]
                    exists.updated_at = datetime.fromisoformat(offer["updated_at"])
                    continue

                session.add(
                    ScrapedOffer(
                        id=offer_uuid,
                        ingestion_run_id=uuid.UUID(job_id),
                        source=offer["source"],
                        source_store_id=offer["source_store_id"],
                        source_product_key=offer["source_product_key"],
                        source_serial_number=offer["source_serial_number"],
                        source_product_name=offer["source_product_name"],
                        source_brand=offer["source_brand"],
                        source_category=offer["source_category"],
                        source_package_quantity=offer["source_package_quantity"],
                        source_package_unit=offer["source_package_unit"],
                        price_eur=offer["price_eur"],
                        currency=offer["currency"],
                        price_type=offer["price_type"],
                        valid_from=datetime.fromisoformat(offer["valid_from"]).date(),
                        valid_to=(
                            datetime.fromisoformat(offer["valid_to"]).date()
                            if offer["valid_to"]
                            else None
                        ),
                        observed_at=datetime.fromisoformat(offer["observed_at"]),
                        canonical_product_id=(
                            uuid.UUID(offer["canonical_product_id"])
                            if offer["canonical_product_id"]
                            else None
                        ),
                        mapping_confidence=offer["mapping_confidence"],
                        needs_review=offer["needs_review"],
                        review_reason=offer["review_reason"],
                        promotion_type=offer["promotion_type"],
                        promotion_label=offer["promotion_label"],
                        raw_payload=offer["raw_payload"],
                        created_at=datetime.fromisoformat(offer["created_at"]),
                        updated_at=datetime.fromisoformat(offer["updated_at"]),
                    )
                )

            for review in self._reviews.values():
                review_uuid = uuid.UUID(review["id"])
                exists = session.get(ScrapedOfferReview, review_uuid)
                if exists:
                    continue
                session.add(
                    ScrapedOfferReview(
                        id=review_uuid,
                        scraped_offer_id=uuid.UUID(review["scraped_offer_id"]),
                        status=review["status"],
                        reviewer_note=review["reviewer_note"],
                        resolved_canonical_product_id=(
                            uuid.UUID(review["resolved_canonical_product_id"])
                            if review["resolved_canonical_product_id"]
                            else None
                        ),
                        created_at=datetime.fromisoformat(review["created_at"]),
                        resolved_at=(
                            datetime.fromisoformat(review["resolved_at"])
                            if review["resolved_at"]
                            else None
                        ),
                        updated_at=datetime.fromisoformat(review["updated_at"]),
                    )
                )
            session.commit()
        return stats

    def seed_default_chains(self) -> None:
        defaults = [
            ("billa", "BILLA", 1),
            ("spar", "SPAR", 1),
            ("hofer", "HOFER", 1),
            ("lidl", "LIDL", 1),
            ("penny", "PENNY", 1),
            ("mpreis", "MPREIS", 1),
            ("unimarkt", "UNIMARKT", 2),
            ("nahfrisch", "Nah&Frisch", 2),
            ("adeg", "ADEG", 2),
        ]
        with SessionLocal() as session:
            for code, name, tier in defaults:
                exists = session.get(ScraperChain, code)
                if exists:
                    continue
                session.add(
                    ScraperChain(
                        code=code,
                        display_name=name,
                        tier=tier,
                        is_active=True,
                        created_at=_utc_now(),
                        updated_at=_utc_now(),
                    )
                )
            session.commit()
