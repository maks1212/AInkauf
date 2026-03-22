from datetime import date

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .algorithm import calculate_optimal_route, detour_check, suggest_brand_alternatives
from .nlp import parse_free_text_item
from .providers.austria_price_provider import HeisspreiseLiveProvider, MockHeisspreiseProvider
from .providers.fuel_provider import EControlFuelProvider
from .schemas import (
    BrandAlternativeRequest,
    BrandAlternativeResponse,
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
    RouteRequest,
    RouteResponse,
)

app = FastAPI(title="AInkauf API", version="0.1.0")
mock_price_provider = MockHeisspreiseProvider()
live_price_provider = HeisspreiseLiveProvider()
fuel_provider = EControlFuelProvider()

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
    limit: int = Query(default=50, ge=1, le=500),
    stores: str | None = Query(
        default=None,
        description="Optional comma-separated store keys (e.g. billa,spar,lidl)",
    ),
) -> LivePricePreviewResponse:
    provider = live_price_provider
    if stores:
        store_keys = tuple(
            key.strip() for key in stores.split(",") if key.strip()
        )
        provider = HeisspreiseLiveProvider(store_keys=store_keys)

    records = await provider.fetch_daily_prices(date.today())
    source = "heisse-preise.io"

    if not records:
        records = await mock_price_provider.fetch_daily_prices(date.today())
        source = "mock-heisspreise"

    return LivePricePreviewResponse(
        source=source,
        count=len(records),
        returned=min(limit, len(records)),
        items=[
            LivePricePreviewItem(
                store_id=record.store_id,
                product_key=record.product_key,
                price_eur=record.price_eur,
                date=record.date.isoformat(),
                source=record.source,
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
