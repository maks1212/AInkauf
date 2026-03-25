from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from .database import Base, SessionLocal, engine
from .providers.austria_price_provider import PriceRecord
from .scraper_admin_models import (
    CanonicalProductCatalog,
    ScrapedOffer,
    ScrapedOfferEvent,
    ScrapedOfferReview,
    ScraperChain,
    ScraperJobRun,
)
from .scraper_admin_store import ScraperAdminStore


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ScraperAdminSqlStore(ScraperAdminStore):
    """
    SQL-backed store that preserves the in-memory store behavior.
    Strategy:
    - Use parent logic for matching/classification/decision/events
    - Persist in-memory state snapshots into SQL for API consumption
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
            "package_quantity": float(row.package_quantity) if row.package_quantity is not None else None,
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
            "source_package_quantity": float(row.source_package_quantity) if row.source_package_quantity is not None else None,
            "source_package_unit": row.source_package_unit,
            "price_eur": float(row.price_eur),
            "currency": row.currency,
            "price_type": row.price_type,
            "valid_from": row.valid_from.isoformat(),
            "valid_to": row.valid_to.isoformat() if row.valid_to else None,
            "observed_at": row.observed_at.isoformat(),
            "canonical_product_id": str(row.canonical_product_id) if row.canonical_product_id else None,
            "mapping_confidence": float(row.mapping_confidence) if row.mapping_confidence is not None else None,
            "needs_review": row.needs_review,
            "review_reason": row.review_reason,
            "promotion_type": row.promotion_type,
            "promotion_label": row.promotion_label,
            "change_type": row.change_type,
            "decision_source": row.decision_source,
            "decision_reason": row.decision_reason,
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
            "resolved_canonical_product_id": str(row.resolved_canonical_product_id) if row.resolved_canonical_product_id else None,
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

    def _row_to_event(self, row: ScrapedOfferEvent) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "scraped_offer_id": str(row.scraped_offer_id),
            "ingestion_run_id": str(row.ingestion_run_id) if row.ingestion_run_id else None,
            "event_type": row.event_type,
            "actor_type": row.actor_type,
            "actor_id": row.actor_id,
            "old_values": row.old_values,
            "new_values": row.new_values,
            "decision_reason": row.decision_reason,
            "rule_id": row.rule_id,
            "confidence": float(row.confidence) if row.confidence is not None else None,
            "comment": row.comment,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }

    def list_canonical_products(self) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            rows = session.scalars(select(CanonicalProductCatalog).order_by(CanonicalProductCatalog.created_at.desc())).all()
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
        created = super().create_canonical_product(
            name=name,
            brand=brand,
            serial_number=serial_number,
            package_quantity=package_quantity,
            package_unit=package_unit,
            category=category,
        )
        with SessionLocal() as session:
            row = CanonicalProductCatalog(
                id=uuid.UUID(created["id"]),
                serial_number=created.get("serial_number"),
                name=created["name"],
                normalized_name=created["normalized_name"],
                brand=created.get("brand"),
                category=created.get("category"),
                package_quantity=created.get("package_quantity"),
                package_unit=created.get("package_unit"),
                created_at=datetime.fromisoformat(created["created_at"]),
                updated_at=datetime.fromisoformat(created["updated_at"]),
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
        updated = super().update_canonical_product(
            product_id=product_id,
            name=name,
            brand=brand,
            serial_number=serial_number,
            package_quantity=package_quantity,
            package_unit=package_unit,
            category=category,
        )
        with SessionLocal() as session:
            row = session.get(CanonicalProductCatalog, uuid.UUID(product_id))
            if row is None:
                raise KeyError("canonical product not found")
            row.name = updated["name"]
            row.normalized_name = updated["normalized_name"]
            row.brand = updated.get("brand")
            row.serial_number = updated.get("serial_number")
            row.package_quantity = updated.get("package_quantity")
            row.package_unit = updated.get("package_unit")
            row.category = updated.get("category")
            row.updated_at = datetime.fromisoformat(updated["updated_at"])
            try:
                session.commit()
            except IntegrityError as exc:
                session.rollback()
                raise ValueError("serial_number already exists.") from exc
            session.refresh(row)
            return self._row_to_product(row)

    def delete_canonical_product(self, product_id: str) -> None:
        super().delete_canonical_product(product_id)
        with SessionLocal() as session:
            row = session.get(CanonicalProductCatalog, uuid.UUID(product_id))
            if row is None:
                raise KeyError("canonical product not found")
            session.delete(row)
            session.commit()
            self._persist_offer_review_event_snapshots(session)

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
        updated = super().update_offer(
            offer_id=offer_id,
            price_eur=price_eur,
            valid_from=valid_from,
            valid_to=valid_to,
            price_type=price_type,
            promotion_type=promotion_type,
            promotion_label=promotion_label,
            canonical_product_id=canonical_product_id,
            needs_review=needs_review,
            review_reason=review_reason,
        )
        with SessionLocal() as session:
            row = session.get(ScrapedOffer, uuid.UUID(offer_id))
            if row is None:
                raise KeyError("offer not found")
            self._apply_offer_dict_to_row(row, updated)
            session.commit()
            self._persist_reviews(session)
            self._persist_events(session)
            session.refresh(row)
            return self._row_to_offer(row)

    def delete_offer(self, offer_id: str) -> None:
        super().delete_offer(offer_id)
        with SessionLocal() as session:
            row = session.get(ScrapedOffer, uuid.UUID(offer_id))
            if row is None:
                raise KeyError("offer not found")
            session.delete(row)
            session.commit()
            self._persist_events(session)

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
        updated_review = super().resolve_review(
            review_id=review_id,
            canonical_product_id=canonical_product_id,
            reviewer_note=reviewer_note,
        )
        with SessionLocal() as session:
            review = session.get(ScrapedOfferReview, uuid.UUID(review_id))
            if review is None:
                raise KeyError("review not found")
            offer = session.get(ScrapedOffer, review.scraped_offer_id)
            if offer is None:
                raise KeyError("offer for review not found")
            latest_offer_dict = self._offers.get(str(offer.id))
            if latest_offer_dict:
                self._apply_offer_dict_to_row(offer, latest_offer_dict)
            review.status = updated_review["status"]
            review.reviewer_note = updated_review.get("reviewer_note")
            review.resolved_canonical_product_id = (
                uuid.UUID(updated_review["resolved_canonical_product_id"])
                if updated_review.get("resolved_canonical_product_id")
                else None
            )
            review.resolved_at = (
                datetime.fromisoformat(updated_review["resolved_at"])
                if updated_review.get("resolved_at")
                else None
            )
            review.updated_at = datetime.fromisoformat(updated_review["updated_at"])
            session.commit()
            self._persist_events(session)
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
            active = session.scalars(select(ScraperJobRun).where(ScraperJobRun.status == "running").limit(1)).first()
            return active is not None

    def start_job(self, *, source: str, stores: list[str]) -> dict[str, Any]:
        in_mem_job = super().start_job(source=source, stores=stores)
        with SessionLocal() as session:
            active = session.scalars(select(ScraperJobRun).where(ScraperJobRun.status == "running").limit(1)).first()
            if active is not None:
                raise RuntimeError("scraper job is already running")
            row = ScraperJobRun(
                id=uuid.UUID(in_mem_job["id"]),
                source=source,
                started_at=datetime.fromisoformat(in_mem_job["started_at"]),
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
        in_mem_job = super().finish_job(
            job_id=job_id,
            status=status,
            record_count=record_count,
            inserted_count=inserted_count,
            matched_count=matched_count,
            review_count=review_count,
            error_count=error_count,
            details=details,
        )
        with SessionLocal() as session:
            row = session.get(ScraperJobRun, uuid.UUID(job_id))
            if row is None:
                raise KeyError("job not found")
            row.status = in_mem_job["status"]
            row.finished_at = datetime.fromisoformat(in_mem_job["finished_at"]) if in_mem_job.get("finished_at") else None
            row.record_count = in_mem_job["record_count"]
            row.inserted_count = in_mem_job["inserted_count"]
            row.matched_count = in_mem_job["matched_count"]
            row.review_count = in_mem_job["review_count"]
            row.error_count = in_mem_job["error_count"]
            row.details = in_mem_job.get("details") or {}
            session.commit()
            self._persist_offer_review_event_snapshots(session)
            session.refresh(row)
            return self._row_to_job(row)

    def ingest_records(
        self,
        *,
        job_id: str,
        records: list[PriceRecord],
        observed_at: datetime | None = None,
    ) -> dict[str, int]:
        stats = super().ingest_records(job_id=job_id, records=records, observed_at=observed_at)
        with SessionLocal() as session:
            self._persist_offer_review_event_snapshots(session)
            session.commit()
        return stats

    def reset_runtime_data(self) -> dict[str, int]:
        in_mem = super().reset_runtime_data()
        with SessionLocal() as session:
            session.query(ScrapedOfferEvent).delete(synchronize_session=False)
            session.query(ScrapedOfferReview).delete(synchronize_session=False)
            session.query(ScrapedOffer).delete(synchronize_session=False)
            session.query(ScraperJobRun).delete(synchronize_session=False)
            session.commit()
        return in_mem

    def list_offer_events(
        self,
        *,
        offer_id: str | None = None,
        event_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            stmt = select(ScrapedOfferEvent).order_by(ScrapedOfferEvent.created_at.desc())
            if offer_id:
                stmt = stmt.where(ScrapedOfferEvent.scraped_offer_id == uuid.UUID(offer_id))
            if event_type:
                stmt = stmt.where(ScrapedOfferEvent.event_type == event_type)
            rows = session.scalars(stmt.offset(max(0, offset)).limit(max(1, min(limit, 2000)))).all()
            return [self._row_to_event(row) for row in rows]

    def list_events(
        self,
        *,
        offer_id: str | None = None,
        event_type: str | None = None,
        actor_type: str | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        with SessionLocal() as session:
            stmt = select(ScrapedOfferEvent).order_by(ScrapedOfferEvent.created_at.desc())
            if offer_id:
                stmt = stmt.where(ScrapedOfferEvent.scraped_offer_id == uuid.UUID(offer_id))
            if event_type:
                stmt = stmt.where(ScrapedOfferEvent.event_type == event_type)
            if actor_type:
                stmt = stmt.where(ScrapedOfferEvent.actor_type == actor_type)
            rows = session.scalars(stmt.offset(max(0, offset)).limit(max(1, min(limit, 2000)))).all()
            return [self._row_to_event(row) for row in rows]

    def _apply_offer_dict_to_row(self, row: ScrapedOffer, data: dict[str, Any]) -> None:
        row.ingestion_run_id = uuid.UUID(data["ingestion_run_id"]) if data.get("ingestion_run_id") else None
        row.source = data["source"]
        row.source_store_id = data["source_store_id"]
        row.source_product_key = data["source_product_key"]
        row.source_serial_number = data.get("source_serial_number")
        row.source_product_name = data["source_product_name"]
        row.source_brand = data.get("source_brand")
        row.source_category = data.get("source_category")
        row.source_package_quantity = data.get("source_package_quantity")
        row.source_package_unit = data.get("source_package_unit")
        row.price_eur = data["price_eur"]
        row.currency = data.get("currency", "EUR")
        row.price_type = data.get("price_type", "regular")
        row.valid_from = datetime.fromisoformat(data["valid_from"]).date()
        row.valid_to = datetime.fromisoformat(data["valid_to"]).date() if data.get("valid_to") else None
        row.observed_at = datetime.fromisoformat(data["observed_at"])
        row.canonical_product_id = uuid.UUID(data["canonical_product_id"]) if data.get("canonical_product_id") else None
        row.mapping_confidence = data.get("mapping_confidence")
        row.needs_review = bool(data.get("needs_review", False))
        row.review_reason = data.get("review_reason")
        row.promotion_type = data.get("promotion_type")
        row.promotion_label = data.get("promotion_label")
        row.change_type = data.get("change_type")
        row.decision_source = data.get("decision_source")
        row.decision_reason = data.get("decision_reason")
        row.raw_payload = data.get("raw_payload")
        row.created_at = datetime.fromisoformat(data["created_at"])
        row.updated_at = datetime.fromisoformat(data["updated_at"])

    def _persist_reviews(self, session) -> None:
        for review_data in self._reviews.values():
            review_uuid = uuid.UUID(review_data["id"])
            row = session.get(ScrapedOfferReview, review_uuid)
            if row is None:
                row = ScrapedOfferReview(id=review_uuid)
                session.add(row)
            row.scraped_offer_id = uuid.UUID(review_data["scraped_offer_id"])
            row.status = review_data["status"]
            row.reviewer_note = review_data.get("reviewer_note")
            row.resolved_canonical_product_id = (
                uuid.UUID(review_data["resolved_canonical_product_id"])
                if review_data.get("resolved_canonical_product_id")
                else None
            )
            row.created_at = datetime.fromisoformat(review_data["created_at"])
            row.resolved_at = datetime.fromisoformat(review_data["resolved_at"]) if review_data.get("resolved_at") else None
            row.updated_at = datetime.fromisoformat(review_data["updated_at"])

    def _persist_events(self, session) -> None:
        for event_data in self._events.values():
            event_uuid = uuid.UUID(event_data["id"])
            row = session.get(ScrapedOfferEvent, event_uuid)
            if row is None:
                row = ScrapedOfferEvent(id=event_uuid)
                session.add(row)
            row.scraped_offer_id = uuid.UUID(event_data["scraped_offer_id"])
            row.ingestion_run_id = (
                uuid.UUID(event_data["ingestion_run_id"]) if event_data.get("ingestion_run_id") else None
            )
            row.event_type = event_data["event_type"]
            row.actor_type = event_data["actor_type"]
            row.actor_id = event_data.get("actor_id")
            row.old_values = event_data.get("old_values")
            row.new_values = event_data.get("new_values")
            row.decision_reason = event_data.get("decision_reason")
            row.rule_id = event_data.get("rule_id")
            row.confidence = event_data.get("confidence")
            row.comment = event_data.get("comment")
            row.created_at = datetime.fromisoformat(event_data["created_at"])

    def _persist_offer_review_event_snapshots(self, session) -> None:
        for offer_data in self._offers.values():
            offer_uuid = uuid.UUID(offer_data["id"])
            row = session.get(ScrapedOffer, offer_uuid)
            if row is None:
                row = ScrapedOffer(id=offer_uuid)
                session.add(row)
            self._apply_offer_dict_to_row(row, offer_data)
        self._persist_reviews(session)
        self._persist_events(session)

    def reset_data(self) -> None:
        super().reset_data()
        with SessionLocal() as session:
            session.execute(delete(ScrapedOfferEvent))
            session.execute(delete(ScrapedOfferReview))
            session.execute(delete(ScrapedOffer))
            session.execute(delete(ScraperJobRun))
            session.commit()

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
