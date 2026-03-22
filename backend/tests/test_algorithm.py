import pytest

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
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            transport_mode="car",
            vehicle_consumption_per_100km=7.0,
            fuel_type="benzin",
        ),
        energy_price_eur_per_unit=1.7,
    )
    assert result.is_worth_it is False
    assert result.net_savings_eur < 0


def test_detour_check_for_bike_has_no_mobility_cost():
    result = detour_check(
        base_total=20.0,
        candidate_total=19.6,
        detour_distance_km=5.0,
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            transport_mode="bike",
        ),
        energy_price_eur_per_unit=None,
    )
    assert result.is_worth_it is True
    assert result.mobility_cost_eur == 0
    assert result.net_savings_eur > 0


def test_route_prefers_nearby_store_if_far_discount_too_small():
    req = RouteRequest(
        shopping_list=[ShoppingListItemInput(name="Aepfel", quantity=2, unit="kg")],
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            transport_mode="car",
            vehicle_consumption_per_100km=7.0,
            fuel_type="benzin",
        ),
        energy_price_eur_per_unit=1.8,
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


def test_route_with_foot_mode_prefers_global_price_minimum():
    req = RouteRequest(
        shopping_list=[ShoppingListItemInput(name="Milch", quantity=1, unit="l")],
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            transport_mode="foot",
            max_reachable_distance_km=20.0,
        ),
        stores=[
            StoreBasket(
                store_id="near-expensive",
                chain="Spar",
                location=Location(lat=48.2090, lng=16.3740),
                basket_total_eur=10.0,
                missing_items=0,
            ),
            StoreBasket(
                store_id="far-cheap",
                chain="Hofer",
                location=Location(lat=48.2800, lng=16.5000),
                basket_total_eur=8.5,
                missing_items=0,
            ),
        ],
    )
    result = calculate_optimal_route(req)
    assert result.recommended_store_id == "far-cheap"


def test_route_with_foot_mode_filters_by_reachability():
    req = RouteRequest(
        shopping_list=[ShoppingListItemInput(name="Brot", quantity=1, unit="stk")],
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            transport_mode="foot",
            max_reachable_distance_km=0.5,
        ),
        stores=[
            StoreBasket(
                store_id="too-far",
                chain="Hofer",
                location=Location(lat=48.2300, lng=16.4500),
                basket_total_eur=2.0,
                missing_items=0,
            ),
        ],
    )
    with pytest.raises(ValueError, match="Keine Maerkte innerhalb der Reichweite"):
        calculate_optimal_route(req)


def test_route_with_foot_mode_respects_carrying_capacity():
    req = RouteRequest(
        shopping_list=[ShoppingListItemInput(name="Wasser", quantity=12, unit="l")],
        user=UserContext(
            location=Location(lat=48.2082, lng=16.3738),
            transport_mode="foot",
            carrying_capacity_kg=5.0,
            max_reachable_distance_km=3.0,
        ),
        stores=[
            StoreBasket(
                store_id="near",
                chain="Spar",
                location=Location(lat=48.2090, lng=16.3740),
                basket_total_eur=8.0,
                missing_items=0,
            ),
        ],
    )
    with pytest.raises(ValueError, match="Einkaufsliste zu schwer"):
        calculate_optimal_route(req)
