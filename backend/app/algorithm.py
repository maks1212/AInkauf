from __future__ import annotations

import math

from .schemas import (
    BrandAlternativeResponse,
    BrandAlternativeSuggestion,
    DetourCheckResponse,
    Location,
    RankedRouteOption,
    RouteMapPoint,
    RouteRequest,
    RouteResponse,
    RouteStoreDecision,
    ShoppingListItemInput,
    StoreProductOffer,
    TransportMode,
    UserContext,
)

NO_NAME_BRANDS_BY_CHAIN: dict[str, set[str]] = {
    "spar": {"s-budget", "s budget"},
    "billa": {"clever"},
    "hofer": {
        "eigenmarke",
        "milfina",
        "milsani",
        "rio d'oro",
        "zurueck zum ursprung",
    },
    "lidl": {
        "eigenmarke",
        "milbona",
        "chef select",
        "combino",
        "w5",
        "cien",
        "lupilu",
    },
}


def _normalize_token(value: str | None) -> str:
    if not value:
        return ""
    return value.strip().casefold().replace("_", " ").replace("-", " ")


def _is_chain_no_name_offer(offer: StoreProductOffer) -> tuple[bool, str | None]:
    chain_key = _normalize_token(offer.chain)
    chain_policy = NO_NAME_BRANDS_BY_CHAIN.get(chain_key)
    offer_brand = _normalize_token(offer.brand)

    if not offer.is_brand_product:
        return True, "non_brand_flag"

    if chain_policy and offer_brand in chain_policy:
        return True, "chain_policy"

    return False, None


def _normalized_quantity_for_pricing(quantity: float, unit: str) -> float:
    normalized_unit = _normalize_token(unit)
    if normalized_unit in {"g"}:
        return quantity / 1000.0
    if normalized_unit in {"ml"}:
        return quantity / 1000.0
    return quantity


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


def _default_reach_km(mode: TransportMode) -> float:
    if mode == TransportMode.foot:
        return 2.5
    if mode == TransportMode.bike:
        return 8.0
    return 1000.0


def _default_capacity_kg(mode: TransportMode) -> float:
    if mode == TransportMode.foot:
        return 8.0
    if mode == TransportMode.bike:
        return 18.0
    return 200.0


def _estimated_item_weight_kg(item: ShoppingListItemInput) -> float:
    if item.estimated_weight_kg is not None:
        return item.estimated_weight_kg

    unit = item.unit.lower().strip()
    if unit == "kg":
        return item.quantity
    if unit == "g":
        return item.quantity / 1000.0
    if unit == "l":
        return item.quantity
    if unit == "ml":
        return item.quantity / 1000.0
    if unit in {"stk", "stueck", "stück"}:
        return item.quantity * 0.2
    if unit in {"pack", "paket"}:
        return item.quantity * 0.5
    return item.quantity * 0.5


def estimate_total_weight_kg(items: list[ShoppingListItemInput]) -> float:
    return sum(_estimated_item_weight_kg(item) for item in items)


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


def suggest_brand_alternatives(
    shopping_list: list[ShoppingListItemInput],
    offers: list[StoreProductOffer],
    prefer_no_name: bool = True,
) -> BrandAlternativeResponse:
    suggestions: list[BrandAlternativeSuggestion] = []

    for item in shopping_list:
        if not item.preferred_brand:
            continue

        preferred_matches = [
            offer
            for offer in offers
            if offer.brand.casefold() == item.preferred_brand.casefold()
            and item.name.casefold() in offer.product_name.casefold()
        ]

        if not preferred_matches:
            continue

        preferred_offer = min(preferred_matches, key=lambda x: x.price_eur)
        alternative_pool = [
            offer
            for offer in offers
            if offer.brand.casefold() != item.preferred_brand.casefold()
            and (
                item.name.casefold() in offer.product_name.casefold()
                or (
                    item.category
                    and offer.category
                    and offer.category.casefold() == item.category.casefold()
                )
            )
        ]
        if not alternative_pool:
            continue

        alternative_offer = min(alternative_pool, key=lambda x: x.price_eur)
        alternative_type = "generic"
        budget_reference = None

        if prefer_no_name:
            no_name_pool: list[StoreProductOffer] = []
            for candidate in alternative_pool:
                is_no_name, reason = _is_chain_no_name_offer(candidate)
                if is_no_name:
                    no_name_pool.append(candidate)
                    if reason == "chain_policy" and budget_reference is None:
                        budget_reference = candidate.brand
            if no_name_pool:
                alternative_offer = min(no_name_pool, key=lambda x: x.price_eur)
                alternative_type = "no_name"
                is_no_name, reason = _is_chain_no_name_offer(alternative_offer)
                if reason == "chain_policy":
                    budget_reference = alternative_offer.brand

        normalized_quantity = _normalized_quantity_for_pricing(item.quantity, item.unit)
        preferred_total = preferred_offer.price_eur * normalized_quantity
        alternative_total = alternative_offer.price_eur * normalized_quantity
        savings = preferred_total - alternative_total

        if savings <= 0:
            continue

        suggestions.append(
            BrandAlternativeSuggestion(
                item_name=item.name,
                preferred_brand=item.preferred_brand,
                preferred_store_id=preferred_offer.store_id,
                preferred_chain=preferred_offer.chain,
                preferred_total_eur=round(preferred_total, 2),
                alternative_brand=alternative_offer.brand,
                alternative_store_id=alternative_offer.store_id,
                alternative_chain=alternative_offer.chain,
                alternative_total_eur=round(alternative_total, 2),
                savings_eur=round(savings, 2),
                alternative_type=alternative_type,
                chain_budget_reference=budget_reference,
            )
        )

    total = round(sum(s.savings_eur for s in suggestions), 2)
    return BrandAlternativeResponse(
        suggestions=suggestions,
        total_potential_savings_eur=total,
    )


def calculate_optimal_route(req: RouteRequest) -> RouteResponse:
    energy_price = resolve_energy_price(
        req.energy_price_eur_per_unit,
        req.fuel_price_eur_per_liter,
    )
    valid_stores = [store for store in req.stores if store.missing_items == 0]
    if not valid_stores:
        raise ValueError("Kein Laden kann alle Produkte liefern.")

    total_weight_kg = estimate_total_weight_kg(req.shopping_list)
    user_mode = req.user.transport_mode

    if user_mode in (TransportMode.foot, TransportMode.bike):
        carrying_capacity = (
            req.user.carrying_capacity_kg
            if req.user.carrying_capacity_kg is not None
            else _default_capacity_kg(user_mode)
        )
        if total_weight_kg > carrying_capacity:
            raise ValueError(
                f"Einkaufsliste zu schwer fuer {user_mode.value}: "
                f"{total_weight_kg:.1f}kg > {carrying_capacity:.1f}kg."
            )

    stores_with_distance = [
        (store, _distance_from_user(req, store.store_id, store.location))
        for store in valid_stores
    ]
    if user_mode in (TransportMode.foot, TransportMode.bike):
        max_reach = (
            req.user.max_reachable_distance_km
            if req.user.max_reachable_distance_km is not None
            else _default_reach_km(user_mode)
        )
        stores_with_distance = [
            (store, distance_km)
            for store, distance_km in stores_with_distance
            if distance_km <= max_reach
        ]
        if not stores_with_distance:
            raise ValueError(
                f"Keine Maerkte innerhalb der Reichweite ({max_reach:.1f}km) fuer {user_mode.value}."
            )

    stores_with_distance.sort(key=lambda row: row[1])

    baseline_store, baseline_distance = stores_with_distance[0]
    baseline_total = baseline_store.basket_total_eur
    baseline_mobility_cost = mobility_cost_eur(
        baseline_distance,
        req.user,
        energy_price_eur_per_unit=energy_price,
    )
    baseline_total_cost = baseline_total + baseline_mobility_cost
    global_min_store = min([row[0] for row in stores_with_distance], key=lambda s: s.basket_total_eur)

    decisions: list[RouteStoreDecision] = []
    ranked_options: list[RankedRouteOption] = []
    best_store_id = baseline_store.store_id
    best_weighted = float("inf")
    best_total = baseline_total_cost

    for store, distance_km in stores_with_distance:
        transport_cost = mobility_cost_eur(
            distance_km,
            req.user,
            energy_price_eur_per_unit=energy_price,
        )
        estimated_total = store.basket_total_eur + transport_cost
        weighted_score = estimated_total + (distance_km * req.distance_weight_eur_per_km)
        net = baseline_total_cost - estimated_total
        include = net >= 0 or store.store_id == baseline_store.store_id

        if weighted_score < best_weighted:
            best_store_id = store.store_id
            best_weighted = weighted_score
            best_total = estimated_total

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
                estimated_total_eur=round(estimated_total, 2),
                weighted_score_eur=round(weighted_score, 2),
                net_savings_vs_baseline_eur=round(net, 2),
                reason=reason,
            )
        )
        ranked_options.append(
            RankedRouteOption(
                rank=0,
                store_id=store.store_id,
                chain=store.chain,
                distance_km=round(distance_km, 2),
                basket_total_eur=round(store.basket_total_eur, 2),
                mobility_cost_eur=round(transport_cost, 2),
                estimated_total_eur=round(estimated_total, 2),
                weighted_score_eur=round(weighted_score, 2),
            )
        )

    ranked_options.sort(key=lambda option: option.weighted_score_eur)
    for index, option in enumerate(ranked_options, start=1):
        option.rank = index

    map_points = [
        RouteMapPoint(
            store_id=store.store_id,
            chain=store.chain,
            location=store.location,
            estimated_total_eur=round(store.basket_total_eur + mobility_cost_eur(
                distance_km,
                req.user,
                energy_price_eur_per_unit=energy_price,
            ), 2),
        )
        for store, distance_km in stores_with_distance
    ]

    return RouteResponse(
        baseline_store_id=baseline_store.store_id,
        global_minimum_store_id=global_min_store.store_id,
        recommended_store_id=best_store_id,
        decisions=decisions,
        ranked_options=ranked_options,
        map_points=map_points,
        estimated_total_eur=round(best_total, 2),
        debug={
            "baseline_distance_km": round(baseline_distance, 2),
            "baseline_total_eur": round(baseline_total, 2),
            "baseline_mobility_cost_eur": round(baseline_mobility_cost, 2),
            "baseline_total_cost_eur": round(baseline_total_cost, 2),
            "estimated_shopping_weight_kg": round(total_weight_kg, 2),
        },
    )
