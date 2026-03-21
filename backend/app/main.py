from datetime import date

from fastapi import FastAPI, HTTPException

from .algorithm import calculate_optimal_route, detour_check, suggest_brand_alternatives
from .nlp import parse_free_text_item
from .providers.austria_price_provider import MockHeisspreiseProvider
from .schemas import (
    BrandAlternativeRequest,
    BrandAlternativeResponse,
    DetourCheckRequest,
    DetourCheckResponse,
    OnboardingInitializeRequest,
    OnboardingInitializeResponse,
    ParseRequest,
    ParseResponse,
    RouteRequest,
    RouteResponse,
)

app = FastAPI(title="AInkauf API", version="0.1.0")
provider = MockHeisspreiseProvider()


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


@app.get("/providers/austria-prices")
async def austria_prices_preview() -> dict[str, object]:
    records = await provider.fetch_daily_prices(date.today())
    return {
        "count": len(records),
        "items": [record.__dict__ for record in records],
    }
