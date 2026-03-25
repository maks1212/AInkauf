from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class ScraperChain(Base):
    __tablename__ = "scraper_chain"

    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    tier: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ScraperStore(Base):
    __tablename__ = "scraper_store"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chain_code: Mapped[str] = mapped_column(
        ForeignKey("scraper_chain.code", ondelete="RESTRICT"),
        nullable=False,
    )
    external_store_id: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    address: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CanonicalProductCatalog(Base):
    __tablename__ = "canonical_product_catalog"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    serial_number: Mapped[str | None] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(255))
    category: Mapped[str | None] = mapped_column(String(120))
    package_quantity: Mapped[float | None] = mapped_column(Numeric(10, 3))
    package_unit: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ScraperJobRun(Base):
    __tablename__ = "scraper_job_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(80), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    store_count: Mapped[int] = mapped_column(Integer, default=0)
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    inserted_count: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    details: Mapped[dict | None] = mapped_column(JSONB)


class ScrapedOffer(Base):
    __tablename__ = "scraped_offer"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_store_id",
            "source_product_key",
            "valid_from",
            "price_type",
            name="uq_scraped_offer_source_store_product_validity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scraper_job_run.id", ondelete="SET NULL")
    )
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_store_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_product_key: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_serial_number: Mapped[str | None] = mapped_column(String(80), index=True)
    source_product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_brand: Mapped[str | None] = mapped_column(String(255))
    source_category: Mapped[str | None] = mapped_column(String(120))
    source_package_quantity: Mapped[float | None] = mapped_column(Numeric(10, 3))
    source_package_unit: Mapped[str | None] = mapped_column(String(20))
    price_eur: Mapped[float] = mapped_column(Numeric(10, 3), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="EUR")
    price_type: Mapped[str] = mapped_column(String(20), nullable=False, default="regular")
    valid_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    valid_to: Mapped[date | None] = mapped_column(Date, index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("canonical_product_catalog.id", ondelete="SET NULL"),
        index=True,
    )
    mapping_confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    needs_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    review_reason: Mapped[str | None] = mapped_column(Text)
    promotion_type: Mapped[str | None] = mapped_column(String(40))
    promotion_label: Mapped[str | None] = mapped_column(String(255))
    change_type: Mapped[str | None] = mapped_column(String(40), index=True)
    decision_source: Mapped[str | None] = mapped_column(String(20))
    decision_reason: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ScrapedOfferReview(Base):
    __tablename__ = "scraped_offer_review"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scraped_offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scraped_offer.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text)
    resolved_canonical_product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("canonical_product_catalog.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class ScrapedOfferEvent(Base):
    __tablename__ = "scraped_offer_event"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scraped_offer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("scraped_offer.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ingestion_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("scraper_job_run.id", ondelete="SET NULL"),
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    actor_type: Mapped[str] = mapped_column(String(20), nullable=False, default="system")
    actor_id: Mapped[str | None] = mapped_column(String(120))
    old_values: Mapped[dict | None] = mapped_column(JSONB)
    new_values: Mapped[dict | None] = mapped_column(JSONB)
    decision_reason: Mapped[str | None] = mapped_column(Text)
    rule_id: Mapped[str | None] = mapped_column(String(80))
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=datetime.utcnow, index=True
    )
