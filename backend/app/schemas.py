from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class FuelType(str, Enum):
    diesel = "diesel"
    benzin = "benzin"


class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class UserContext(BaseModel):
    location: Location
    vehicle_consumption_l_per_100km: float = Field(..., gt=0)
    fuel_type: FuelType


class ShoppingListItemInput(BaseModel):
    name: str
    quantity: float = Field(..., gt=0)
    unit: str


class StoreBasket(BaseModel):
    store_id: str
    chain: str
    location: Location
    basket_total_eur: float = Field(..., ge=0)
    missing_items: int = Field(default=0, ge=0)


class DetourCheckRequest(BaseModel):
    base_store_total_eur: float = Field(..., ge=0)
    candidate_store_total_eur: float = Field(..., ge=0)
    detour_distance_km: float = Field(default=5.0, ge=0)
    user: UserContext
    fuel_price_eur_per_liter: float = Field(..., gt=0)


class DetourCheckResponse(BaseModel):
    is_worth_it: bool
    gross_savings_eur: float
    fuel_cost_eur: float
    net_savings_eur: float
    explanation: str


class RouteRequest(BaseModel):
    shopping_list: list[ShoppingListItemInput]
    user: UserContext
    fuel_price_eur_per_liter: float = Field(..., gt=0)
    stores: list[StoreBasket]
    distance_matrix_km: dict[str, dict[str, float]] | None = None


class RouteStoreDecision(BaseModel):
    store_id: str
    included: bool
    distance_km: float
    basket_total_eur: float
    fuel_cost_eur: float
    net_savings_vs_baseline_eur: float
    reason: str


class RouteResponse(BaseModel):
    baseline_store_id: str
    global_minimum_store_id: str
    recommended_store_id: str
    decisions: list[RouteStoreDecision]
    estimated_total_eur: float
    debug: dict[str, Any] = Field(default_factory=dict)


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ParseResponse(BaseModel):
    quantity: float
    unit: str
    product_name: str
