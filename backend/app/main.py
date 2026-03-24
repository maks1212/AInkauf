from datetime import date
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .algorithm import calculate_optimal_route, detour_check, suggest_brand_alternatives
from .nlp import parse_free_text_item
from .providers.austria_price_provider import HeisspreiseLiveProvider
from .providers.fuel_provider import EControlFuelProvider
from .price_platform_read_model import BasketItemRequest, PricePlatformReadModel
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

app = FastAPI(title="AInkauf API", version="0.1.0")
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
