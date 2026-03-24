from datetime import date
from datetime import datetime
from contextlib import asynccontextmanager
from html import escape

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from .algorithm import calculate_optimal_route, detour_check, suggest_brand_alternatives
from .nlp import parse_free_text_item
from .providers.austria_price_provider import HeisspreiseLiveProvider
from .providers.fuel_provider import EControlFuelProvider
from .price_platform_read_model import BasketItemRequest, PricePlatformReadModel
from .config import get_settings
from .scraper_admin_service import ScraperAdminService
from .scraper_admin_store import ScraperAdminStore
from .schemas import (
    BrandAlternativeRequest,
    BrandAlternativeResponse,
    ProviderCatalogItem,
    ProviderCatalogResponse,
    DetourCheckRequest,
    DetourCheckResponse,
    FuelType,
    LiveFuelQuoteResponse,
    LivePricePreviewItem,
    LivePricePreviewResponse,
    OnboardingInitializeRequest,
    OnboardingInitializeResponse,
    ParseRequest,
    ParseResponse,
    PricePlatformBasketQuoteRequest,
    PricePlatformBasketQuoteResponse,
    PricePlatformBasketQuoteStore,
    PricePlatformChainItem,
    PricePlatformChainsResponse,
    PricePlatformCurrentPriceResponse,
    PricePlatformPriceHistoryResponse,
    PricePlatformPriceRecord,
    PricePlatformPromotionResponse,
    PricePlatformStoreItem,
    PricePlatformStoresResponse,
    RouteRequest,
    RouteResponse,
)

settings = get_settings()
scraper_admin_store = ScraperAdminStore()
scraper_admin_service = ScraperAdminService(
    store=scraper_admin_store,
    settings=settings,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    scraper_admin_service.start_scheduler()
    try:
        yield
    finally:
        await scraper_admin_service.stop_scheduler()


app = FastAPI(title="AInkauf API", version="0.1.0", lifespan=lifespan)
live_price_provider = HeisspreiseLiveProvider()
fuel_provider = EControlFuelProvider()
price_platform_read_model = PricePlatformReadModel()

# Web frontend runs on a separate origin during development (e.g. :8090).
# Allow cross-origin JSON requests so onboarding/optimization calls work in browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/nlp/parse-item", response_model=ParseResponse)
def parse_item(req: ParseRequest) -> ParseResponse:
    try:
        return parse_free_text_item(req.text)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/optimization/detour-worth-it", response_model=DetourCheckResponse)
def detour_worth_it(req: DetourCheckRequest) -> DetourCheckResponse:
    return detour_check(
        base_total=req.base_store_total_eur,
        candidate_total=req.candidate_store_total_eur,
        detour_distance_km=req.detour_distance_km,
        user=req.user,
        energy_price_eur_per_unit=(
            req.energy_price_eur_per_unit
            if req.energy_price_eur_per_unit is not None
            else req.fuel_price_eur_per_liter
        ),
    )


@app.post("/optimization/calculate-optimal-route", response_model=RouteResponse)
def optimal_route(req: RouteRequest) -> RouteResponse:
    try:
        return calculate_optimal_route(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/optimization/brand-alternatives", response_model=BrandAlternativeResponse)
def brand_alternatives(req: BrandAlternativeRequest) -> BrandAlternativeResponse:
    return suggest_brand_alternatives(
        shopping_list=req.shopping_list,
        offers=req.offers,
        prefer_no_name=req.prefer_no_name,
    )


@app.post("/onboarding/initialize", response_model=OnboardingInitializeResponse)
def onboarding_initialize(req: OnboardingInitializeRequest) -> OnboardingInitializeResponse:
    # Validation is performed in the UserContext schema.
    return OnboardingInitializeResponse(
        onboarding_ready=True,
        message="Onboarding abgeschlossen. Du kannst jetzt deine Einkaufsliste eingeben.",
        next_step="shopping_list_input",
        defaults={
            "max_reachable_distance_foot_km": 2.5,
            "max_reachable_distance_bike_km": 8.0,
            "default_carrying_capacity_foot_kg": 8.0,
            "default_carrying_capacity_bike_kg": 18.0,
        },
    )


@app.get("/providers/austria-prices", response_model=LivePricePreviewResponse)
async def austria_prices_preview(
    limit: int = Query(default=50, ge=1, le=20000),
    stores: str | None = Query(
        default=None,
        description="Optional comma-separated store keys (e.g. billa,spar,lidl)",
    ),
    search: str | None = Query(
        default=None,
        description="Optional comma-separated search terms applied to product_key.",
    ),
) -> LivePricePreviewResponse:
    provider = live_price_provider
    if stores:
        store_keys = tuple(
            key.strip() for key in stores.split(",") if key.strip()
        )
        provider = HeisspreiseLiveProvider(store_keys=store_keys)

    records = await provider.fetch_daily_prices(date.today())
    if search:
        terms = [term.strip().casefold() for term in search.split(",") if term.strip()]
        if terms:
            records = [
                record
                for record in records
                if any(term in record.product_key.casefold() for term in terms)
            ]
    if not records:
        raise HTTPException(
            status_code=502,
            detail=(
                "No live grocery price records available from heisse-preise.io "
                "for the requested store selection."
            ),
        )

    return LivePricePreviewResponse(
        source="heisse-preise.io",
        count=len(records),
        returned=min(limit, len(records)),
        items=[
            LivePricePreviewItem(
                store_id=record.store_id,
                product_key=record.product_key,
                price_eur=record.price_eur,
                date=record.date.isoformat(),
                source=record.source,
                package_quantity=record.package_quantity,
                package_unit=record.package_unit,
            )
            for record in records[:limit]
        ],
    )


@app.get("/providers/fuel-price-live", response_model=LiveFuelQuoteResponse)
async def fuel_price_live(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    fuel_type: FuelType = Query(...),
) -> LiveFuelQuoteResponse:
    try:
        quote = await fuel_provider.get_cheapest_quote(
            lat=lat,
            lng=lng,
            fuel_type=fuel_type.value,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502,
            detail=f"Fuel provider unavailable: {exc}",
        ) from exc

    return LiveFuelQuoteResponse(
        fuel_type=fuel_type,
        price_eur_per_unit=quote.price_eur_per_unit,
        station_name=quote.station_name,
        station_address=quote.station_address,
        distance_km=quote.distance_km,
        source=quote.source,
        note=quote.note,
    )


@app.get("/providers/catalog", response_model=ProviderCatalogResponse)
def providers_catalog() -> ProviderCatalogResponse:
    return ProviderCatalogResponse(
        items=[
            ProviderCatalogItem(
                id="econtrol-sprit",
                domain="fuel",
                data_type="station prices",
                status="live",
                notes="Official Austrian fuel station prices for DIE/SUP/GAS via public API.",
                auth_required=False,
                docs_url="https://api.e-control.at/sprit/1.0/doc/index.html",
            ),
            ProviderCatalogItem(
                id="heisse-preise",
                domain="grocery",
                data_type="product prices",
                status="live",
                notes="Austrian supermarket product datasets in compressed canonical JSON files.",
                auth_required=False,
                docs_url="https://heisse-preise.io/",
            ),
            ProviderCatalogItem(
                id="openfoodfacts-open-prices",
                domain="grocery",
                data_type="crowdsourced prices",
                status="candidate",
                notes="Global crowdsourced receipt prices; useful as enrichment and fallback.",
                auth_required=False,
                docs_url="https://prices.openfoodfacts.org/api/docs",
            ),
            ProviderCatalogItem(
                id="preisrunter-api",
                domain="grocery",
                data_type="aggregated retailer prices",
                status="candidate",
                notes="Austrian price aggregation API with limited free tier and API key access.",
                auth_required=True,
                docs_url="https://preisrunter.at/api/",
            ),
        ]
    )


@app.get("/price-platform/chains", response_model=PricePlatformChainsResponse)
def list_price_platform_chains() -> PricePlatformChainsResponse:
    return PricePlatformChainsResponse(
        items=[
            PricePlatformChainItem(
                code=chain.code,
                display_name=chain.display_name,
                tier=chain.tier,
            )
            for chain in price_platform_read_model.list_chains()
        ]
    )


@app.get("/price-platform/stores", response_model=PricePlatformStoresResponse)
def list_price_platform_stores(
    chain: str | None = Query(default=None),
    lat: float | None = Query(default=None, ge=-90, le=90),
    lng: float | None = Query(default=None, ge=-180, le=180),
    radius_km: float | None = Query(default=None, ge=0),
) -> PricePlatformStoresResponse:
    if (lat is None) != (lng is None):
        raise HTTPException(
            status_code=422,
            detail="lat and lng must be provided together.",
        )
    rows = price_platform_read_model.list_stores(
        chain=chain,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
    )
    return PricePlatformStoresResponse(
        items=[
            PricePlatformStoreItem(
                store_id=store.store_id,
                chain=store.chain,
                name=store.name,
                lat=store.lat,
                lng=store.lng,
                address=store.address,
                distance_km=distance,
            )
            for store, distance in rows
        ]
    )


@app.get(
    "/price-platform/prices/current",
    response_model=PricePlatformCurrentPriceResponse,
)
def get_price_platform_current_price(
    store_id: str = Query(...),
    product_key: str = Query(...),
    on_date: str | None = Query(default=None),
) -> PricePlatformCurrentPriceResponse:
    parsed_date = date.today()
    if on_date:
        try:
            parsed_date = date.fromisoformat(on_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="on_date must be ISO format YYYY-MM-DD",
            ) from exc

    record = price_platform_read_model.get_current_price(
        store_id=store_id,
        product_key=product_key,
        on_date=parsed_date,
    )
    if record is None:
        raise HTTPException(
            status_code=404,
            detail="No current price found for store/product.",
        )

    return PricePlatformCurrentPriceResponse(
        item=PricePlatformPriceRecord(
            store_id=record.store_id,
            product_key=record.product_key,
            product_name=record.product_name,
            brand=record.brand,
            category=record.category,
            package_quantity=record.package_quantity,
            package_unit=record.package_unit,
            price_eur=record.price_eur,
            price_type=record.price_type,
            valid_from=record.valid_from.isoformat(),
            valid_to=record.valid_to.isoformat() if record.valid_to else None,
            source=record.source,
            promotion_type=record.promotion_type,
            promotion_label=record.promotion_label,
        )
    )


@app.get(
    "/price-platform/prices/history",
    response_model=PricePlatformPriceHistoryResponse,
)
def get_price_platform_history(
    store_id: str = Query(...),
    product_key: str = Query(...),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
) -> PricePlatformPriceHistoryResponse:
    parsed_from: date | None = None
    parsed_to: date | None = None

    if from_date:
        try:
            parsed_from = date.fromisoformat(from_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="from_date must be ISO format YYYY-MM-DD",
            ) from exc
    if to_date:
        try:
            parsed_to = date.fromisoformat(to_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="to_date must be ISO format YYYY-MM-DD",
            ) from exc

    records = price_platform_read_model.get_price_history(
        store_id=store_id,
        product_key=product_key,
        from_date=parsed_from,
        to_date=parsed_to,
    )

    return PricePlatformPriceHistoryResponse(
        items=[
            PricePlatformPriceRecord(
                store_id=record.store_id,
                product_key=record.product_key,
                product_name=record.product_name,
                brand=record.brand,
                category=record.category,
                package_quantity=record.package_quantity,
                package_unit=record.package_unit,
                price_eur=record.price_eur,
                price_type=record.price_type,
                valid_from=record.valid_from.isoformat(),
                valid_to=record.valid_to.isoformat() if record.valid_to else None,
                source=record.source,
                promotion_type=record.promotion_type,
                promotion_label=record.promotion_label,
            )
            for record in records
        ]
    )


@app.get(
    "/price-platform/promotions/current",
    response_model=PricePlatformPromotionResponse,
)
def get_current_promotions(
    chain: str | None = Query(default=None),
    store_id: str | None = Query(default=None),
    on_date: str | None = Query(default=None),
) -> PricePlatformPromotionResponse:
    parsed_date = date.today()
    if on_date:
        try:
            parsed_date = date.fromisoformat(on_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="on_date must be ISO format YYYY-MM-DD",
            ) from exc

    records = price_platform_read_model.get_current_promotions(
        chain=chain,
        store_id=store_id,
        on_date=parsed_date,
    )
    return PricePlatformPromotionResponse(
        items=[
            PricePlatformPriceRecord(
                store_id=record.store_id,
                product_key=record.product_key,
                product_name=record.product_name,
                brand=record.brand,
                category=record.category,
                package_quantity=record.package_quantity,
                package_unit=record.package_unit,
                price_eur=record.price_eur,
                price_type=record.price_type,
                valid_from=record.valid_from.isoformat(),
                valid_to=record.valid_to.isoformat() if record.valid_to else None,
                source=record.source,
                promotion_type=record.promotion_type,
                promotion_label=record.promotion_label,
            )
            for record in records
        ]
    )


@app.post(
    "/price-platform/basket/quote",
    response_model=PricePlatformBasketQuoteResponse,
)
def quote_basket(req: PricePlatformBasketQuoteRequest) -> PricePlatformBasketQuoteResponse:
    parsed_date = date.today()
    if req.on_date:
        try:
            parsed_date = date.fromisoformat(req.on_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail="on_date must be ISO format YYYY-MM-DD",
            ) from exc

    quote_rows = price_platform_read_model.quote_basket(
        items=[
            BasketItemRequest(
                product_key=item.product_key,
                quantity=item.quantity,
                unit=item.unit,
            )
            for item in req.items
        ],
        store_ids=req.store_ids,
        on_date=parsed_date,
    )
    return PricePlatformBasketQuoteResponse(
        quotes=[PricePlatformBasketQuoteStore.model_validate(row) for row in quote_rows]
    )


# ----------------------------
# Scraper Admin API + Minimal UI
# ----------------------------

@app.get("/admin/scraper/catalog")
def admin_list_catalog() -> dict:
    return {"items": scraper_admin_store.list_canonical_products()}


@app.post("/admin/scraper/catalog")
def admin_create_catalog_item(payload: dict) -> dict:
    try:
        item = scraper_admin_store.create_canonical_product(
            name=str(payload.get("name", "")).strip(),
            brand=payload.get("brand"),
            serial_number=payload.get("serial_number"),
            package_quantity=payload.get("package_quantity"),
            package_unit=payload.get("package_unit"),
            category=payload.get("category"),
        )
        return {"item": item}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/admin/scraper/catalog/{product_id}")
def admin_update_catalog_item(product_id: str, payload: dict) -> dict:
    try:
        item = scraper_admin_store.update_canonical_product(
            product_id=product_id,
            name=payload.get("name"),
            brand=payload.get("brand"),
            serial_number=payload.get("serial_number"),
            package_quantity=payload.get("package_quantity"),
            package_unit=payload.get("package_unit"),
            category=payload.get("category"),
        )
        return {"item": item}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/admin/scraper/catalog/{product_id}")
def admin_delete_catalog_item(product_id: str) -> dict:
    try:
        scraper_admin_store.delete_canonical_product(product_id)
        return {"deleted": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/admin/scraper/offers")
def admin_list_offers(
    needs_review: bool | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict:
    return {
        "items": scraper_admin_store.list_offers(needs_review=needs_review, limit=limit)
    }


@app.patch("/admin/scraper/offers/{offer_id}")
def admin_update_offer(offer_id: str, payload: dict) -> dict:
    try:
        item = scraper_admin_store.update_offer(
            offer_id=offer_id,
            price_eur=payload.get("price_eur"),
            valid_from=payload.get("valid_from"),
            valid_to=payload.get("valid_to"),
            price_type=payload.get("price_type"),
            promotion_type=payload.get("promotion_type"),
            promotion_label=payload.get("promotion_label"),
            canonical_product_id=payload.get("canonical_product_id"),
            needs_review=payload.get("needs_review"),
            review_reason=payload.get("review_reason"),
        )
        return {"item": item}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/admin/scraper/offers/{offer_id}")
def admin_delete_offer(offer_id: str) -> dict:
    try:
        scraper_admin_store.delete_offer(offer_id)
        return {"deleted": True}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/admin/scraper/reviews")
def admin_list_reviews(
    status: str = Query(default="pending"),
    limit: int = Query(default=200, ge=1, le=2000),
) -> dict:
    return {"items": scraper_admin_store.list_reviews(status=status, limit=limit)}


@app.post("/admin/scraper/reviews/{review_id}/resolve")
def admin_resolve_review(review_id: str, payload: dict) -> dict:
    canonical_product_id = payload.get("canonical_product_id")
    if not canonical_product_id:
        raise HTTPException(status_code=400, detail="canonical_product_id is required")
    try:
        item = scraper_admin_store.resolve_review(
            review_id=review_id,
            canonical_product_id=canonical_product_id,
            reviewer_note=payload.get("reviewer_note"),
        )
        return {"item": item}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/admin/scraper/config")
def admin_get_config() -> dict:
    return {
        "config": scraper_admin_store.get_config(),
        "schedule_recommendation": scraper_admin_service.scheduling_recommendation(),
    }


@app.patch("/admin/scraper/config")
def admin_update_config(payload: dict) -> dict:
    config = scraper_admin_store.update_config(
        enabled=payload.get("enabled"),
        interval_minutes=payload.get("interval_minutes"),
        max_parallel_stores=payload.get("max_parallel_stores"),
        retries=payload.get("retries"),
    )
    return {"config": config}


@app.get("/admin/scraper/jobs")
def admin_list_jobs(limit: int = Query(default=40, ge=1, le=500)) -> dict:
    return {
        "running": scraper_admin_store.is_running(),
        "items": scraper_admin_store.list_jobs(limit=limit),
    }


@app.post("/admin/scraper/jobs/start")
async def admin_start_job(payload: dict | None = None) -> dict:
    body = payload or {}
    stores = body.get("stores")
    simulate = bool(body.get("simulate", False))
    if stores is not None and not isinstance(stores, list):
        raise HTTPException(status_code=400, detail="stores must be an array of store keys")
    try:
        job = scraper_admin_service.start_manual_job(
            stores=stores,
            simulate=simulate,
        )
        return {"job": job}
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get("/admin/scraper/ui", response_class=HTMLResponse)
def admin_scraper_ui() -> str:
    jobs = scraper_admin_store.list_jobs(limit=20)
    reviews = scraper_admin_store.list_reviews(status="pending", limit=40)
    offers = scraper_admin_store.list_offers(needs_review=None, limit=50)
    catalog = scraper_admin_store.list_canonical_products()
    config = scraper_admin_store.get_config()
    recommendation = scraper_admin_service.scheduling_recommendation()

    def _rows(items: list[dict], keys: list[str]) -> str:
        if not items:
            return "<tr><td colspan='99'><em>Keine Daten</em></td></tr>"
        rendered = []
        for row in items:
            rendered.append(
                "<tr>"
                + "".join(f"<td>{escape(str(row.get(key, '')))}</td>" for key in keys)
                + "</tr>"
            )
        return "".join(rendered)

    return f"""
<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8" />
    <title>AInkauf Scraper Admin</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 20px; }}
      h1, h2 {{ margin-bottom: 8px; }}
      .card {{ border: 1px solid #ddd; padding: 12px; margin-bottom: 18px; border-radius: 6px; }}
      table {{ border-collapse: collapse; width: 100%; }}
      th, td {{ border: 1px solid #ddd; padding: 6px; font-size: 12px; text-align: left; }}
      th {{ background: #f6f6f6; }}
      .hint {{ color: #444; font-size: 13px; }}
      code {{ background: #f4f4f4; padding: 2px 4px; }}
    </style>
  </head>
  <body>
    <h1>AInkauf Scraper Admin</h1>
    <p class="hint">CRUD + Review Queue + Job Start + Scheduler-Konfig. Fuer Schreiben bitte die JSON APIs darunter verwenden.</p>
    <div class="card">
      <h2>Konfiguration</h2>
      <p><strong>enabled:</strong> {escape(str(config.get("enabled")))}, <strong>interval_minutes:</strong> {escape(str(config.get("interval_minutes")))}, <strong>max_parallel_stores:</strong> {escape(str(config.get("max_parallel_stores")))}, <strong>retries:</strong> {escape(str(config.get("retries")))}</p>
      <p class="hint">Empfohlenes Intervall: <strong>{escape(str(recommendation.get("recommended_interval_minutes")))}</strong> Minuten. Minimum: {escape(str(recommendation.get("min_interval_minutes")))}.</p>
      <p class="hint">"Ein Thread pro Geschäft" ist nicht empfohlen. Besser: begrenzte Worker (z. B. 4) + Retry/Backoff.</p>
    </div>
    <div class="card">
      <h2>API Quick Actions</h2>
      <ul>
        <li>Job starten: <code>POST /admin/scraper/jobs/start</code> Body: {{"stores":["billa","spar"],"simulate":false}}</li>
        <li>Scheduler setzen: <code>PATCH /admin/scraper/config</code> Body: {{"enabled":true,"interval_minutes":180,"max_parallel_stores":4,"retries":2}}</li>
        <li>Katalog CRUD: <code>/admin/scraper/catalog</code></li>
        <li>Offers CRUD: <code>/admin/scraper/offers</code></li>
        <li>Review Queue: <code>/admin/scraper/reviews</code> und <code>/admin/scraper/reviews/{{id}}/resolve</code></li>
      </ul>
    </div>
    <div class="card">
      <h2>Jobs</h2>
      <table>
        <thead><tr><th>id</th><th>status</th><th>source</th><th>store_count</th><th>record_count</th><th>inserted</th><th>matched</th><th>review</th><th>errors</th><th>started_at</th><th>finished_at</th></tr></thead>
        <tbody>{_rows(jobs, ["id", "status", "source", "store_count", "record_count", "inserted_count", "matched_count", "review_count", "error_count", "started_at", "finished_at"])}</tbody>
      </table>
    </div>
    <div class="card">
      <h2>Review Queue (pending)</h2>
      <table>
        <thead><tr><th>id</th><th>scraped_offer_id</th><th>status</th><th>review_reason</th><th>created_at</th></tr></thead>
        <tbody>{_rows(reviews, ["id", "scraped_offer_id", "status", "review_reason", "created_at"])}</tbody>
      </table>
    </div>
    <div class="card">
      <h2>Offers (letzte 50)</h2>
      <table>
        <thead><tr><th>id</th><th>source_store_id</th><th>source_product_key</th><th>price_eur</th><th>valid_from</th><th>valid_to</th><th>canonical_product_id</th><th>needs_review</th><th>review_reason</th></tr></thead>
        <tbody>{_rows(offers, ["id", "source_store_id", "source_product_key", "price_eur", "valid_from", "valid_to", "canonical_product_id", "needs_review", "review_reason"])}</tbody>
      </table>
    </div>
    <div class="card">
      <h2>Katalog (Canonical Products)</h2>
      <table>
        <thead><tr><th>id</th><th>name</th><th>brand</th><th>serial_number</th><th>package_quantity</th><th>package_unit</th><th>category</th><th>updated_at</th></tr></thead>
        <tbody>{_rows(catalog, ["id", "name", "brand", "serial_number", "package_quantity", "package_unit", "category", "updated_at"])}</tbody>
      </table>
    </div>
  </body>
</html>
    """
