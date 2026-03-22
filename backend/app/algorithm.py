from __future__ import annotations

import math

from .schemas import (
    DetourCheckResponse,
    Location,
    RouteRequest,
    RouteResponse,
    RouteStoreDecision,
    TransportMode,
    UserContext,
)


def haversine_km(a: Location, b: Location) -> float:
    radius = 6371.0
    d_lat = math.radians(b.lat - a.lat)
    d_lng = math.radians(b.lng - a.lng)
    lat1 = math.radians(a.lat)
    lat2 = math.radians(b.lat)

    h = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lng / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(h))


def resolve_energy_price(energy_price_eur_per_unit: float | None, legacy_fuel_price: float | None) -> float | None:
    return energy_price_eur_per_unit if energy_price_eur_per_unit is not None else legacy_fuel_price


def mobility_cost_eur(
    distance_km: float,
    user: UserContext,
    energy_price_eur_per_unit: float | None,
    default_transit_cost_per_km: float = 0.40,
) -> float:
    if user.transport_mode in (TransportMode.foot, TransportMode.bike):
        return 0.0

    if user.transport_mode == TransportMode.transit:
        transit_cost = (
            user.transit_cost_per_km_eur
            if user.transit_cost_per_km_eur is not None
            else default_transit_cost_per_km
        )
        return distance_km * transit_cost

    if user.vehicle_consumption_per_100km is None:
        raise ValueError("vehicle_consumption_per_100km fehlt fuer car mode.")
    if energy_price_eur_per_unit is None:
        raise ValueError("energy_price_eur_per_unit (oder fuel_price_eur_per_liter) fehlt fuer car mode.")

    return (distance_km / 100.0) * user.vehicle_consumption_per_100km * energy_price_eur_per_unit


def detour_check(
    base_total: float,
    candidate_total: float,
    detour_distance_km: float,
    user: UserContext,
    energy_price_eur_per_unit: float | None,
) -> DetourCheckResponse:
    gross_savings = base_total - candidate_total
    transport_cost = mobility_cost_eur(
        detour_distance_km,
        user,
        energy_price_eur_per_unit=energy_price_eur_per_unit,
    )
    net = gross_savings - transport_cost
    is_worth_it = net >= 0

    explanation = (
        "Umweg wirtschaftlich sinnvoll."
        if is_worth_it
        else "Umweg nicht sinnvoll, da Mobilitaetskosten die Ersparnis aufzehren."
    )

    return DetourCheckResponse(
        is_worth_it=is_worth_it,
        gross_savings_eur=round(gross_savings, 2),
        mobility_cost_eur=round(transport_cost, 2),
        fuel_cost_eur=round(transport_cost, 2),
        net_savings_eur=round(net, 2),
        explanation=explanation,
    )


def _distance_from_user(req: RouteRequest, store_id: str, store_location: Location) -> float:
    if req.distance_matrix_km and req.distance_matrix_km.get("user", {}).get(store_id) is not None:
        return req.distance_matrix_km["user"][store_id]
    return haversine_km(req.user.location, store_location)


def calculate_optimal_route(req: RouteRequest) -> RouteResponse:
    energy_price = resolve_energy_price(
        req.energy_price_eur_per_unit,
        req.fuel_price_eur_per_liter,
    )
    valid_stores = [store for store in req.stores if store.missing_items == 0]
    if not valid_stores:
        raise ValueError("Kein Laden kann alle Produkte liefern.")

    stores_with_distance = [
        (store, _distance_from_user(req, store.store_id, store.location))
        for store in valid_stores
    ]
    stores_with_distance.sort(key=lambda row: row[1])

    baseline_store, baseline_distance = stores_with_distance[0]
    baseline_total = baseline_store.basket_total_eur
    global_min_store = min(valid_stores, key=lambda s: s.basket_total_eur)

    decisions: list[RouteStoreDecision] = []
    best_store_id = baseline_store.store_id
    best_net = 0.0
    best_total = baseline_total

    for store, distance_km in stores_with_distance:
        extra_distance_km = max(0.0, distance_km - baseline_distance)
        transport_cost = mobility_cost_eur(
            extra_distance_km,
            req.user,
            energy_price_eur_per_unit=energy_price,
        )
        net = (baseline_total - store.basket_total_eur) - transport_cost
        include = net >= 0 or store.store_id == baseline_store.store_id

        if include and net > best_net:
            best_store_id = store.store_id
            best_net = net
            best_total = store.basket_total_eur + transport_cost

        reason = "Basisladen (naechster vollstaendiger Warenkorb)"
        if store.store_id != baseline_store.store_id:
            reason = (
                "Eingeschlossen: Netto-Ersparnis >= 0"
                if include
                else "Ausgeschlossen: Netto-Ersparnis < 0"
            )

        decisions.append(
            RouteStoreDecision(
                store_id=store.store_id,
                included=include,
                distance_km=round(distance_km, 2),
                basket_total_eur=round(store.basket_total_eur, 2),
                mobility_cost_eur=round(transport_cost, 2),
                fuel_cost_eur=round(transport_cost, 2),
                net_savings_vs_baseline_eur=round(net, 2),
                reason=reason,
            )
        )

    return RouteResponse(
        baseline_store_id=baseline_store.store_id,
        global_minimum_store_id=global_min_store.store_id,
        recommended_store_id=best_store_id,
        decisions=decisions,
        estimated_total_eur=round(best_total, 2),
        debug={
            "baseline_distance_km": round(baseline_distance, 2),
            "baseline_total_eur": round(baseline_total, 2),
        },
    )
