from app.algorithm import calculate_optimal_route, detour_check
from app.schemas import (
    Location,
    RouteRequest,
    ShoppingListItemInput,
    StoreBasket,
    UserContext,
)


def test_detour_check_for_5km_not_worth_it():
    result = detour_check(
        base_total=20.0,
        candidate_total=19.6,
        detour_distance_km=5.0,
        consumption_l_per_100km=7.0,
        fuel_price=1.7,
    )
    assert result.is_worth_it is False
    assert result.net_savings_eur < 0


def test_route_prefers_nearby_store_if_far_discount_too_small():
    req = RouteRequest(
        shopping_list=[ShoppingListItemInput(name="Aepfel", quantity=2, unit="kg")],
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            vehicle_consumption_l_per_100km=7.0,
            fuel_type="benzin",
        ),
        fuel_price_eur_per_liter=1.8,
        stores=[
            StoreBasket(
                store_id="near",
                chain="Spar",
                location=Location(lat=48.2090, lng=16.3740),
                basket_total_eur=30.0,
                missing_items=0,
            ),
            StoreBasket(
                store_id="far-cheaper",
                chain="Hofer",
                location=Location(lat=48.2800, lng=16.5000),
                basket_total_eur=29.8,
                missing_items=0,
            ),
        ],
    )
    result = calculate_optimal_route(req)
    assert result.baseline_store_id == "near"
    assert result.recommended_store_id == "near"
