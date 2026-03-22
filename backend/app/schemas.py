from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, model_validator


class FuelType(str, Enum):
    diesel = "diesel"
    benzin = "benzin"
    autogas = "autogas"
    strom = "strom"


class TransportMode(str, Enum):
    car = "car"
    foot = "foot"
    bike = "bike"
    transit = "transit"


class Location(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)


class UserContext(BaseModel):
    location: Location
    transport_mode: TransportMode = TransportMode.car
    vehicle_consumption_per_100km: float | None = Field(
        default=None,
        gt=0,
        validation_alias=AliasChoices(
            "vehicle_consumption_per_100km",
            "vehicle_consumption_l_per_100km",
        ),
    )
    fuel_type: FuelType | None = None
    transit_cost_per_km_eur: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_mode_specific_fields(self) -> "UserContext":
        if self.transport_mode == TransportMode.car:
            if self.vehicle_consumption_per_100km is None:
                raise ValueError("vehicle_consumption_per_100km is required for car mode.")
            if self.fuel_type is None:
                raise ValueError("fuel_type is required for car mode.")
        return self


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
    energy_price_eur_per_unit: float | None = Field(default=None, gt=0)
    # backward-compatible field name for older clients
    fuel_price_eur_per_liter: float | None = Field(default=None, gt=0)


class DetourCheckResponse(BaseModel):
    is_worth_it: bool
    gross_savings_eur: float
    mobility_cost_eur: float
    fuel_cost_eur: float
    net_savings_eur: float
    explanation: str


class RouteRequest(BaseModel):
    shopping_list: list[ShoppingListItemInput]
    user: UserContext
    energy_price_eur_per_unit: float | None = Field(default=None, gt=0)
    # backward-compatible field name for older clients
    fuel_price_eur_per_liter: float | None = Field(default=None, gt=0)
    stores: list[StoreBasket]
    distance_matrix_km: dict[str, dict[str, float]] | None = None


class RouteStoreDecision(BaseModel):
    store_id: str
    included: bool
    distance_km: float
    basket_total_eur: float
    mobility_cost_eur: float
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
