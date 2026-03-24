from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

from .config import Settings
from .providers.austria_price_provider import HeisspreiseLiveProvider, PriceRecord
from .scraper_admin_store import ScraperAdminStore


class ScraperAdminService:
    def __init__(
        self,
        *,
        store: ScraperAdminStore,
        settings: Settings,
    ) -> None:
        self.store = store
        self.settings = settings
        self._scheduler_task: asyncio.Task | None = None
        self._job_tasks: dict[str, asyncio.Task] = {}

        # Apply startup defaults from config.
        self.store.update_config(
            enabled=settings.scraper_scheduler_enabled,
            interval_minutes=settings.scraper_schedule_interval_minutes,
            max_parallel_stores=settings.scraper_max_parallel_stores,
            retries=settings.scraper_store_fetch_retries,
        )

    def start_scheduler(self) -> None:
        if self._scheduler_task is not None and not self._scheduler_task.done():
            return
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop_scheduler(self) -> None:
        if self._scheduler_task is not None:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

    def scheduling_recommendation(self) -> dict[str, Any]:
        return {
            "recommended_interval_minutes": 180,
            "min_interval_minutes": 30,
            "reasoning": [
                "Most grocery sources update in batches, not continuously.",
                "3h interval is a stable baseline for broad chain coverage.",
                "For promotion-sensitive dashboards use 60m during daytime.",
                "Below 30m increases source load and failure risk significantly.",
            ],
            "strategy": {
                "night_window_00_06": 360,
                "day_window_06_22": 180,
                "promo_peak_window": 60,
            },
        }

    async def _scheduler_loop(self) -> None:
        while True:
            await asyncio.sleep(30)
            config = self.store.get_config()
            if not config.get("enabled", False):
                continue
            if self.store.is_running():
                continue
            if not self._is_due_for_next_run(config.get("interval_minutes", 180)):
                continue
            try:
                self.start_manual_job(simulate=False)
            except RuntimeError:
                continue

    def _is_due_for_next_run(self, interval_minutes: int) -> bool:
        jobs = self.store.list_jobs(limit=1)
        if not jobs:
            return True
        last = jobs[0]
        reference = last.get("finished_at") or last.get("started_at")
        if not reference:
            return True
        try:
            last_time = datetime.fromisoformat(reference)
        except ValueError:
            return True
        delta_minutes = (datetime.utcnow() - last_time).total_seconds() / 60.0
        return delta_minutes >= max(15, interval_minutes)

    def _default_store_keys(self) -> list[str]:
        return list(HeisspreiseLiveProvider.DEFAULT_STORE_KEYS)

    def start_manual_job(
        self,
        *,
        stores: list[str] | None = None,
        simulate: bool = False,
    ) -> dict[str, Any]:
        # Ensure we have an active loop before marking job as running.
        asyncio.get_running_loop()
        selected_stores = [item.strip() for item in (stores or self._default_store_keys()) if item.strip()]
        if not selected_stores:
            selected_stores = self._default_store_keys()
        source = "simulation" if simulate else "heisse-preise.io"
        job = self.store.start_job(source=source, stores=selected_stores)
        task = asyncio.create_task(
            self._run_job(
                job_id=job["id"],
                stores=selected_stores,
                simulate=simulate,
            )
        )
        self._job_tasks[job["id"]] = task
        task.add_done_callback(lambda _task, job_id=job["id"]: self._job_tasks.pop(job_id, None))
        return job

    async def _run_job(self, *, job_id: str, stores: list[str], simulate: bool) -> None:
        try:
            if simulate:
                records = self._simulate_records(stores=stores)
            else:
                config = self.store.get_config()
                provider = HeisspreiseLiveProvider(
                    store_keys=tuple(stores),
                    max_parallel_stores=int(config.get("max_parallel_stores", 4)),
                    retries=int(config.get("retries", 2)),
                )
                records = await provider.fetch_daily_prices(day=date.today())

            stats = self.store.ingest_records(job_id=job_id, records=records)
            self.store.finish_job(
                job_id=job_id,
                status="success",
                record_count=stats["record_count"],
                inserted_count=stats["inserted_count"],
                matched_count=stats["matched_count"],
                review_count=stats["review_count"],
                error_count=0,
                details={
                    "stores": stores,
                    "simulate": simulate,
                },
            )
        except Exception as exc:  # noqa: BLE001
            self.store.finish_job(
                job_id=job_id,
                status="failed",
                record_count=0,
                inserted_count=0,
                matched_count=0,
                review_count=0,
                error_count=1,
                details={
                    "stores": stores,
                    "simulate": simulate,
                    "error": str(exc),
                },
            )

    def _simulate_records(self, *, stores: list[str]) -> list[PriceRecord]:
        today = date.today()
        results: list[PriceRecord] = []
        for store in stores:
            results.append(
                PriceRecord(
                    store_id=f"{store}-demo",
                    product_key="gouda_g",
                    price_eur=2.19,
                    date=today,
                    source="simulation",
                    package_quantity=250,
                    package_unit="g",
                )
            )
            results.append(
                PriceRecord(
                    store_id=f"{store}-demo",
                    product_key="pizza_margherita_stk",
                    price_eur=2.79,
                    date=today,
                    source="simulation",
                    package_quantity=1,
                    package_unit="stk",
                )
            )
        return results
