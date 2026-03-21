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
    carrying_capacity_kg: float | None = Field(default=None, gt=0)
    max_reachable_distance_km: float | None = Field(default=None, ge=0)

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
    preferred_brand: str | None = None
    category: str | None = None
    estimated_weight_kg: float | None = Field(default=None, ge=0)


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
    distance_weight_eur_per_km: float = Field(default=0.08, ge=0)


class RouteStoreDecision(BaseModel):
    store_id: str
    included: bool
    distance_km: float
    basket_total_eur: float
    mobility_cost_eur: float
    fuel_cost_eur: float
    estimated_total_eur: float
    weighted_score_eur: float
    net_savings_vs_baseline_eur: float
    reason: str


class RankedRouteOption(BaseModel):
    rank: int
    store_id: str
    chain: str
    distance_km: float
    basket_total_eur: float
    mobility_cost_eur: float
    estimated_total_eur: float
    weighted_score_eur: float


class RouteMapPoint(BaseModel):
    store_id: str
    chain: str
    location: Location
    estimated_total_eur: float


class RouteResponse(BaseModel):
    baseline_store_id: str
    global_minimum_store_id: str
    recommended_store_id: str
    decisions: list[RouteStoreDecision]
    ranked_options: list[RankedRouteOption]
    map_points: list[RouteMapPoint]
    estimated_total_eur: float
    debug: dict[str, Any] = Field(default_factory=dict)


class StoreProductOffer(BaseModel):
    store_id: str
    chain: str
    product_name: str
    brand: str
    category: str | None = None
    unit: str
    price_eur: float = Field(..., ge=0)
    is_brand_product: bool = False


class BrandAlternativeRequest(BaseModel):
    shopping_list: list[ShoppingListItemInput]
    offers: list[StoreProductOffer]


class BrandAlternativeSuggestion(BaseModel):
    item_name: str
    preferred_brand: str
    preferred_store_id: str
    preferred_chain: str
    preferred_total_eur: float
    alternative_brand: str
    alternative_store_id: str
    alternative_chain: str
    alternative_total_eur: float
    savings_eur: float


class BrandAlternativeResponse(BaseModel):
    suggestions: list[BrandAlternativeSuggestion]
    total_potential_savings_eur: float


class OnboardingInitializeRequest(BaseModel):
    user: UserContext


class OnboardingInitializeResponse(BaseModel):
    onboarding_ready: bool
    message: str
    next_step: str
    defaults: dict[str, float]


class ParseRequest(BaseModel):
    text: str = Field(..., min_length=1)


class ParseResponse(BaseModel):
    quantity: float
    unit: str
    product_name: str
