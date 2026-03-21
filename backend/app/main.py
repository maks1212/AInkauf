from datetime import date

from fastapi import FastAPI, HTTPException

from .algorithm import calculate_optimal_route, detour_check
from .nlp import parse_free_text_item
from .providers.austria_price_provider import MockHeisspreiseProvider
from .schemas import (
    DetourCheckRequest,
    DetourCheckResponse,
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


@app.get("/providers/austria-prices")
async def austria_prices_preview() -> dict[str, object]:
    records = await provider.fetch_daily_prices(date.today())
    return {
        "count": len(records),
        "items": [record.__dict__ for record in records],
    }
