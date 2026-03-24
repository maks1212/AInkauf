from datetime import date
from datetime import datetime
from contextlib import asynccontextmanager
from html import escape
from urllib.parse import urlencode

from fastapi import FastAPI, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

from .algorithm import calculate_optimal_route, detour_check, suggest_brand_alternatives
from .nlp import parse_free_text_item
from .providers.austria_price_provider import HeisspreiseLiveProvider
from .providers.fuel_provider import EControlFuelProvider
from .price_platform_read_model import BasketItemRequest, PricePlatformReadModel
from .config import get_settings
from .scraper_admin_service import ScraperAdminService
from .scraper_admin_store import ScraperAdminStore
from .scraper_admin_store_sql import ScraperAdminSqlStore
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
if settings.scraper_admin_use_persistence:
    scraper_admin_store = ScraperAdminSqlStore()
    if settings.scraper_admin_auto_create_tables:
        scraper_admin_store.create_schema()
        scraper_admin_store.seed_default_chains()
else:
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


@app.post("/admin/scraper/bootstrap")
def admin_bootstrap_persistence() -> dict:
    if not isinstance(scraper_admin_store, ScraperAdminSqlStore):
        raise HTTPException(
            status_code=400,
            detail=(
                "Persistence store is disabled. Set scraper_admin_use_persistence=true "
                "to use SQL persistence."
            ),
        )
    scraper_admin_store.create_schema()
    scraper_admin_store.seed_default_chains()
    return {"bootstrapped": True}


def _ui_params(
    *,
    offers_page: int = 1,
    offers_page_size: int = 25,
    offers_needs_review: str = "all",
    reviews_page: int = 1,
    reviews_page_size: int = 25,
    reviews_status: str = "pending",
    notice: str | None = None,
    error: str | None = None,
) -> dict[str, str]:
    params = {
        "offers_page": str(max(1, offers_page)),
        "offers_page_size": str(max(1, min(200, offers_page_size))),
        "offers_needs_review": offers_needs_review,
        "reviews_page": str(max(1, reviews_page)),
        "reviews_page_size": str(max(1, min(200, reviews_page_size))),
        "reviews_status": reviews_status,
    }
    if notice:
        params["notice"] = notice
    if error:
        params["error"] = error
    return params


def _redirect_ui(params: dict[str, str]) -> RedirectResponse:
    return RedirectResponse(
        url=f"/admin/scraper/ui?{urlencode(params)}",
        status_code=303,
    )


def _safe_return_url(return_url: str | None) -> str | None:
    if return_url and return_url.startswith("/admin/scraper/ui"):
        return return_url
    return None


@app.post("/admin/scraper/form/jobs/start")
async def admin_form_start_job(
    stores_csv: str = Form(default="billa,spar,lidl"),
    simulate: bool = Form(default=False),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    stores = [entry.strip() for entry in stores_csv.split(",") if entry.strip()]
    try:
        await admin_start_job({"stores": stores, "simulate": simulate})
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Job gestartet"))
    except HTTPException as exc:
        return _redirect_ui(_ui_params(error=f"Job-Start fehlgeschlagen: {exc.detail}"))


@app.post("/admin/scraper/form/config/update")
def admin_form_update_config(
    enabled: bool = Form(default=False),
    interval_minutes: int = Form(default=180),
    max_parallel_stores: int = Form(default=4),
    retries: int = Form(default=2),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    admin_update_config(
        {
            "enabled": enabled,
            "interval_minutes": interval_minutes,
            "max_parallel_stores": max_parallel_stores,
            "retries": retries,
        }
    )
    safe = _safe_return_url(return_url)
    if safe:
        return RedirectResponse(url=safe, status_code=303)
    return _redirect_ui(_ui_params(notice="Konfiguration gespeichert"))


@app.post("/admin/scraper/form/bootstrap")
def admin_form_bootstrap(return_url: str | None = Form(default=None)) -> RedirectResponse:
    try:
        admin_bootstrap_persistence()
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Persistence bootstrap erfolgreich"))
    except HTTPException as exc:
        return _redirect_ui(_ui_params(error=f"Bootstrap fehlgeschlagen: {exc.detail}"))


@app.post("/admin/scraper/form/catalog/create")
def admin_form_create_catalog(
    name: str = Form(...),
    brand: str = Form(default=""),
    serial_number: str = Form(default=""),
    package_quantity: str = Form(default=""),
    package_unit: str = Form(default=""),
    category: str = Form(default=""),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    try:
        admin_create_catalog_item(
            {
                "name": name,
                "brand": brand or None,
                "serial_number": serial_number or None,
                "package_quantity": float(package_quantity) if package_quantity.strip() else None,
                "package_unit": package_unit or None,
                "category": category or None,
            }
        )
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Katalog-Artikel erstellt"))
    except Exception as exc:  # noqa: BLE001
        return _redirect_ui(_ui_params(error=f"Katalog-Create fehlgeschlagen: {exc}"))


@app.post("/admin/scraper/form/catalog/update")
def admin_form_update_catalog(
    product_id: str = Form(...),
    name: str = Form(default=""),
    brand: str = Form(default=""),
    serial_number: str = Form(default=""),
    package_quantity: str = Form(default=""),
    package_unit: str = Form(default=""),
    category: str = Form(default=""),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    try:
        admin_update_catalog_item(
            product_id,
            {
                "name": name,
                "brand": brand or None,
                "serial_number": serial_number or None,
                "package_quantity": float(package_quantity) if package_quantity.strip() else None,
                "package_unit": package_unit or None,
                "category": category or None,
            },
        )
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Katalog-Artikel aktualisiert"))
    except Exception as exc:  # noqa: BLE001
        return _redirect_ui(_ui_params(error=f"Katalog-Update fehlgeschlagen: {exc}"))


@app.post("/admin/scraper/form/catalog/delete")
def admin_form_delete_catalog(
    product_id: str = Form(...),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    try:
        admin_delete_catalog_item(product_id)
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Katalog-Artikel geloescht"))
    except Exception as exc:  # noqa: BLE001
        return _redirect_ui(_ui_params(error=f"Katalog-Delete fehlgeschlagen: {exc}"))


@app.post("/admin/scraper/form/offers/update")
def admin_form_update_offer(
    offer_id: str = Form(...),
    price_eur: str = Form(default=""),
    valid_from: str = Form(default=""),
    valid_to: str = Form(default=""),
    price_type: str = Form(default="regular"),
    promotion_type: str = Form(default=""),
    promotion_label: str = Form(default=""),
    canonical_product_id: str = Form(default=""),
    needs_review: bool = Form(default=False),
    review_reason: str = Form(default=""),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    try:
        admin_update_offer(
            offer_id,
            {
                "price_eur": float(price_eur) if price_eur.strip() else None,
                "valid_from": valid_from or None,
                "valid_to": valid_to or None,
                "price_type": price_type or None,
                "promotion_type": promotion_type or None,
                "promotion_label": promotion_label or None,
                "canonical_product_id": canonical_product_id or None,
                "needs_review": needs_review,
                "review_reason": review_reason or None,
            },
        )
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Offer aktualisiert"))
    except Exception as exc:  # noqa: BLE001
        return _redirect_ui(_ui_params(error=f"Offer-Update fehlgeschlagen: {exc}"))


@app.post("/admin/scraper/form/offers/delete")
def admin_form_delete_offer(
    offer_id: str = Form(...),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    try:
        admin_delete_offer(offer_id)
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Offer geloescht"))
    except Exception as exc:  # noqa: BLE001
        return _redirect_ui(_ui_params(error=f"Offer-Delete fehlgeschlagen: {exc}"))


@app.post("/admin/scraper/form/reviews/resolve")
def admin_form_resolve_review(
    review_id: str = Form(...),
    canonical_product_id: str = Form(...),
    reviewer_note: str = Form(default=""),
    return_url: str | None = Form(default=None),
) -> RedirectResponse:
    try:
        admin_resolve_review(
            review_id,
            {
                "canonical_product_id": canonical_product_id,
                "reviewer_note": reviewer_note or None,
            },
        )
        safe = _safe_return_url(return_url)
        if safe:
            return RedirectResponse(url=safe, status_code=303)
        return _redirect_ui(_ui_params(notice="Review aufgeloest"))
    except Exception as exc:  # noqa: BLE001
        return _redirect_ui(_ui_params(error=f"Review-Resolve fehlgeschlagen: {exc}"))


@app.get("/admin/scraper/ui", response_class=HTMLResponse)
def admin_scraper_ui(
    offers_page: int = Query(default=1, ge=1),
    offers_page_size: int = Query(default=25, ge=1, le=200),
    offers_needs_review: str = Query(default="all"),
    reviews_page: int = Query(default=1, ge=1),
    reviews_page_size: int = Query(default=25, ge=1, le=200),
    reviews_status: str = Query(default="pending"),
    notice: str | None = Query(default=None),
    error: str | None = Query(default=None),
) -> str:
    jobs = scraper_admin_store.list_jobs(limit=30)
    needs_review_filter = None
    if offers_needs_review.lower() == "true":
        needs_review_filter = True
    elif offers_needs_review.lower() == "false":
        needs_review_filter = False

    offers_limit = min(2000, offers_page * offers_page_size)
    all_offers = scraper_admin_store.list_offers(
        needs_review=needs_review_filter,
        limit=offers_limit,
    )
    offers_start = (offers_page - 1) * offers_page_size
    paged_offers = all_offers[offers_start : offers_start + offers_page_size]
    offers_has_prev = offers_page > 1
    offers_has_next = len(all_offers) > offers_start + offers_page_size

    reviews_limit = min(2000, reviews_page * reviews_page_size)
    all_reviews = scraper_admin_store.list_reviews(status=reviews_status, limit=reviews_limit)
    reviews_start = (reviews_page - 1) * reviews_page_size
    paged_reviews = all_reviews[reviews_start : reviews_start + reviews_page_size]
    reviews_has_prev = reviews_page > 1
    reviews_has_next = len(all_reviews) > reviews_start + reviews_page_size

    catalog = scraper_admin_store.list_canonical_products()
    config = scraper_admin_store.get_config()
    recommendation = scraper_admin_service.scheduling_recommendation()
    return_url = (
        "/admin/scraper/ui?"
        + urlencode(
            _ui_params(
                offers_page=offers_page,
                offers_page_size=offers_page_size,
                offers_needs_review=offers_needs_review,
                reviews_page=reviews_page,
                reviews_page_size=reviews_page_size,
                reviews_status=reviews_status,
            )
        )
    )

    def _rows(items: list[dict], keys: list[str], actions: str | None = None) -> str:
        if not items:
            colspan = len(keys) + (1 if actions else 0)
            return f"<tr><td colspan='{colspan}'><em>Keine Daten</em></td></tr>"
        rendered = []
        for row in items:
            action_cell = ""
            if actions is not None:
                action_cell = f"<td>{actions.format(**{key: escape(str(value)) for key, value in row.items()})}</td>"
            rendered.append(
                "<tr>"
                + "".join(f"<td>{escape(str(row.get(key, '')))}</td>" for key in keys)
                + action_cell
                + "</tr>"
            )
        return "".join(rendered)

    catalog_options = "".join(
        f"<option value='{escape(item['id'])}'>{escape(item['name'])} ({escape(str(item.get('brand') or '-'))})</option>"
        for item in catalog
    )

    offers_prev_form = (
        f"""
        <form method="get" action="/admin/scraper/ui">
          <input type="hidden" name="offers_page" value="{offers_page - 1}" />
          <input type="hidden" name="offers_page_size" value="{offers_page_size}" />
          <input type="hidden" name="offers_needs_review" value="{escape(offers_needs_review)}" />
          <input type="hidden" name="reviews_page" value="{reviews_page}" />
          <input type="hidden" name="reviews_page_size" value="{reviews_page_size}" />
          <input type="hidden" name="reviews_status" value="{escape(reviews_status)}" />
          <button type="submit">Offers Zurueck</button>
        </form>
        """
        if offers_has_prev
        else ""
    )
    offers_next_form = (
        f"""
        <form method="get" action="/admin/scraper/ui">
          <input type="hidden" name="offers_page" value="{offers_page + 1}" />
          <input type="hidden" name="offers_page_size" value="{offers_page_size}" />
          <input type="hidden" name="offers_needs_review" value="{escape(offers_needs_review)}" />
          <input type="hidden" name="reviews_page" value="{reviews_page}" />
          <input type="hidden" name="reviews_page_size" value="{reviews_page_size}" />
          <input type="hidden" name="reviews_status" value="{escape(reviews_status)}" />
          <button type="submit">Offers Weiter</button>
        </form>
        """
        if offers_has_next
        else ""
    )
    reviews_prev_form = (
        f"""
        <form method="get" action="/admin/scraper/ui">
          <input type="hidden" name="offers_page" value="{offers_page}" />
          <input type="hidden" name="offers_page_size" value="{offers_page_size}" />
          <input type="hidden" name="offers_needs_review" value="{escape(offers_needs_review)}" />
          <input type="hidden" name="reviews_page" value="{reviews_page - 1}" />
          <input type="hidden" name="reviews_page_size" value="{reviews_page_size}" />
          <input type="hidden" name="reviews_status" value="{escape(reviews_status)}" />
          <button type="submit">Reviews Zurueck</button>
        </form>
        """
        if reviews_has_prev
        else ""
    )
    reviews_next_form = (
        f"""
        <form method="get" action="/admin/scraper/ui">
          <input type="hidden" name="offers_page" value="{offers_page}" />
          <input type="hidden" name="offers_page_size" value="{offers_page_size}" />
          <input type="hidden" name="offers_needs_review" value="{escape(offers_needs_review)}" />
          <input type="hidden" name="reviews_page" value="{reviews_page + 1}" />
          <input type="hidden" name="reviews_page_size" value="{reviews_page_size}" />
          <input type="hidden" name="reviews_status" value="{escape(reviews_status)}" />
          <button type="submit">Reviews Weiter</button>
        </form>
        """
        if reviews_has_next
        else ""
    )

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
      .row-actions form {{ display: inline-block; margin-right: 6px; }}
      .form-grid {{ display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 8px; }}
      .pager {{ display: flex; gap: 8px; margin-top: 8px; }}
      input, select, button {{ font-size: 12px; padding: 5px; }}
      .ok {{ background: #e8f7e8; border: 1px solid #b5dfb5; padding: 8px; margin-bottom: 10px; }}
      .err {{ background: #fdecec; border: 1px solid #f2b6b6; padding: 8px; margin-bottom: 10px; }}
    </style>
  </head>
  <body>
    <h1>AInkauf Scraper Admin</h1>
    <p class="hint">Alle Funktionen koennen direkt ueber Formulare/Buttons ausgeloesst werden.</p>
    {"<div class='ok'>" + escape(notice) + "</div>" if notice else ""}
    {"<div class='err'>" + escape(error) + "</div>" if error else ""}

    <div class="card">
      <h2>Job starten</h2>
      <form method="post" action="/admin/scraper/form/jobs/start">
        <input type="hidden" name="return_url" value="{escape(return_url)}" />
        <label>Stores CSV <input type="text" name="stores_csv" value="billa,spar,lidl" style="width:320px" /></label>
        <label><input type="checkbox" name="simulate" /> Simulation</label>
        <button type="submit">Scraper Job starten</button>
      </form>
    </div>

    <div class="card">
      <h2>Konfiguration</h2>
      <p><strong>enabled:</strong> {escape(str(config.get("enabled")))}, <strong>interval_minutes:</strong> {escape(str(config.get("interval_minutes")))}, <strong>max_parallel_stores:</strong> {escape(str(config.get("max_parallel_stores")))}, <strong>retries:</strong> {escape(str(config.get("retries")))}</p>
      <p class="hint">Empfohlenes Intervall: <strong>{escape(str(recommendation.get("recommended_interval_minutes")))}</strong> Minuten. Minimum: {escape(str(recommendation.get("min_interval_minutes")))}.</p>
      <p class="hint">"Ein Thread pro Geschäft" ist nicht empfohlen. Besser: begrenzte Worker (z. B. 4) + Retry/Backoff.</p>
      <form method="post" action="/admin/scraper/form/config/update">
        <input type="hidden" name="return_url" value="{escape(return_url)}" />
        <label><input type="checkbox" name="enabled" {"checked" if config.get("enabled") else ""} /> Scheduler aktiv</label>
        <label>Intervall (Min) <input type="number" name="interval_minutes" value="{escape(str(config.get("interval_minutes")))}" min="15" /></label>
        <label>Worker <input type="number" name="max_parallel_stores" value="{escape(str(config.get("max_parallel_stores")))}" min="1" max="16" /></label>
        <label>Retries <input type="number" name="retries" value="{escape(str(config.get("retries")))}" min="0" max="5" /></label>
        <button type="submit">Konfiguration speichern</button>
      </form>
      <form method="post" action="/admin/scraper/form/bootstrap" style="margin-top:8px;">
        <input type="hidden" name="return_url" value="{escape(return_url)}" />
        <button type="submit">Persistence Bootstrap</button>
      </form>
    </div>

    <div class="card">
      <h2>Katalog: neuen Artikel anlegen</h2>
      <form method="post" action="/admin/scraper/form/catalog/create" class="form-grid">
        <input type="hidden" name="return_url" value="{escape(return_url)}" />
        <input type="text" name="name" placeholder="Name" required />
        <input type="text" name="brand" placeholder="Marke" />
        <input type="text" name="serial_number" placeholder="Seriennummer/EAN" />
        <input type="number" step="0.001" name="package_quantity" placeholder="Menge" />
        <input type="text" name="package_unit" placeholder="Einheit" />
        <input type="text" name="category" placeholder="Kategorie" />
        <button type="submit">Katalog-Artikel erstellen</button>
      </form>
    </div>

    <div class="card">
      <h2>Jobs</h2>
      <table>
        <thead><tr><th>id</th><th>status</th><th>source</th><th>store_count</th><th>record_count</th><th>inserted</th><th>matched</th><th>review</th><th>errors</th><th>started_at</th><th>finished_at</th></tr></thead>
        <tbody>{_rows(jobs, ["id", "status", "source", "store_count", "record_count", "inserted_count", "matched_count", "review_count", "error_count", "started_at", "finished_at"])}</tbody>
      </table>
    </div>
    <div class="card">
      <h2>Review Queue</h2>
      <form method="get" action="/admin/scraper/ui">
        <input type="hidden" name="offers_page" value="{offers_page}" />
        <input type="hidden" name="offers_page_size" value="{offers_page_size}" />
        <input type="hidden" name="offers_needs_review" value="{escape(offers_needs_review)}" />
        <label>Status
          <select name="reviews_status">
            <option value="pending" {"selected" if reviews_status == "pending" else ""}>pending</option>
            <option value="resolved" {"selected" if reviews_status == "resolved" else ""}>resolved</option>
            <option value="all" {"selected" if reviews_status == "all" else ""}>all</option>
          </select>
        </label>
        <label>Page size <input type="number" name="reviews_page_size" value="{reviews_page_size}" min="1" max="200" /></label>
        <input type="hidden" name="reviews_page" value="1" />
        <button type="submit">Review Filter anwenden</button>
      </form>
      <table>
        <thead><tr><th>id</th><th>scraped_offer_id</th><th>status</th><th>review_reason</th><th>created_at</th><th>Aktion</th></tr></thead>
        <tbody>{_rows(
            paged_reviews,
            ["id", "scraped_offer_id", "status", "review_reason", "created_at"],
            actions='''
                <form method="post" action="/admin/scraper/form/reviews/resolve" class="row-actions">
                  <input type="hidden" name="review_id" value="{id}" />
                  <input type="hidden" name="return_url" value="''' + escape(return_url) + '''" />
                  <select name="canonical_product_id" required>
                    ''' + catalog_options + '''
                  </select>
                  <input type="text" name="reviewer_note" placeholder="Notiz" />
                  <button type="submit">Resolve</button>
                </form>
            '''
        )}</tbody>
      </table>
      <div class="pager">{reviews_prev_form}{reviews_next_form}</div>
    </div>
    <div class="card">
      <h2>Offers</h2>
      <form method="get" action="/admin/scraper/ui">
        <input type="hidden" name="reviews_page" value="{reviews_page}" />
        <input type="hidden" name="reviews_page_size" value="{reviews_page_size}" />
        <input type="hidden" name="reviews_status" value="{escape(reviews_status)}" />
        <label>needs_review
          <select name="offers_needs_review">
            <option value="all" {"selected" if offers_needs_review == "all" else ""}>all</option>
            <option value="true" {"selected" if offers_needs_review == "true" else ""}>true</option>
            <option value="false" {"selected" if offers_needs_review == "false" else ""}>false</option>
          </select>
        </label>
        <label>Page size <input type="number" name="offers_page_size" value="{offers_page_size}" min="1" max="200" /></label>
        <input type="hidden" name="offers_page" value="1" />
        <button type="submit">Offer Filter anwenden</button>
      </form>
      <table>
        <thead><tr><th>id</th><th>source_store_id</th><th>source_product_key</th><th>price_eur</th><th>valid_from</th><th>valid_to</th><th>canonical_product_id</th><th>needs_review</th><th>review_reason</th><th>Aktion</th></tr></thead>
        <tbody>{_rows(
            paged_offers,
            ["id", "source_store_id", "source_product_key", "price_eur", "valid_from", "valid_to", "canonical_product_id", "needs_review", "review_reason"],
            actions='''
                <form method="post" action="/admin/scraper/form/offers/update" class="row-actions">
                  <input type="hidden" name="offer_id" value="{id}" />
                  <input type="hidden" name="return_url" value="''' + escape(return_url) + '''" />
                  <input type="number" step="0.001" name="price_eur" value="{price_eur}" style="width:80px" />
                  <select name="price_type">
                    <option value="regular">regular</option>
                    <option value="promo">promo</option>
                  </select>
                  <input type="text" name="canonical_product_id" value="{canonical_product_id}" placeholder="canonical id" style="width:170px" />
                  <label><input type="checkbox" name="needs_review" /> review</label>
                  <input type="text" name="review_reason" value="{review_reason}" placeholder="reason" style="width:120px" />
                  <button type="submit">Update</button>
                </form>
                <form method="post" action="/admin/scraper/form/offers/delete" class="row-actions">
                  <input type="hidden" name="offer_id" value="{id}" />
                  <input type="hidden" name="return_url" value="''' + escape(return_url) + '''" />
                  <button type="submit">Delete</button>
                </form>
            '''
        )}</tbody>
      </table>
      <div class="pager">{offers_prev_form}{offers_next_form}</div>
    </div>
    <div class="card">
      <h2>Katalog (Canonical Products)</h2>
      <table>
        <thead><tr><th>id</th><th>name</th><th>brand</th><th>serial_number</th><th>package_quantity</th><th>package_unit</th><th>category</th><th>updated_at</th><th>Aktion</th></tr></thead>
        <tbody>{_rows(
            catalog,
            ["id", "name", "brand", "serial_number", "package_quantity", "package_unit", "category", "updated_at"],
            actions='''
                <form method="post" action="/admin/scraper/form/catalog/update" class="row-actions">
                  <input type="hidden" name="product_id" value="{id}" />
                  <input type="hidden" name="return_url" value="''' + escape(return_url) + '''" />
                  <input type="text" name="name" value="{name}" style="width:130px" />
                  <input type="text" name="brand" value="{brand}" style="width:90px" />
                  <input type="text" name="serial_number" value="{serial_number}" style="width:120px" />
                  <input type="text" name="package_quantity" value="{package_quantity}" style="width:70px" />
                  <input type="text" name="package_unit" value="{package_unit}" style="width:60px" />
                  <input type="text" name="category" value="{category}" style="width:90px" />
                  <button type="submit">Update</button>
                </form>
                <form method="post" action="/admin/scraper/form/catalog/delete" class="row-actions">
                  <input type="hidden" name="product_id" value="{id}" />
                  <input type="hidden" name="return_url" value="''' + escape(return_url) + '''" />
                  <button type="submit">Delete</button>
                </form>
            '''
        )}</tbody>
      </table>
    </div>
  </body>
</html>
    """
