class ParsedItem {
  final double quantity;
  final String unit;
  final String productName;

  ParsedItem({
    required this.quantity,
    required this.unit,
    required this.productName,
  });

  factory ParsedItem.fromJson(Map<String, dynamic> json) {
    return ParsedItem(
      quantity: (json['quantity'] as num).toDouble(),
      unit: json['unit'] as String,
      productName: json['product_name'] as String,
    );
  }
}

class DetourDecision {
  final bool isWorthIt;
  final double grossSavingsEur;
  final double mobilityCostEur;
  final double fuelCostEur;
  final double netSavingsEur;
  final String explanation;

  DetourDecision({
    required this.isWorthIt,
    required this.grossSavingsEur,
    required this.mobilityCostEur,
    required this.fuelCostEur,
    required this.netSavingsEur,
    required this.explanation,
  });

  factory DetourDecision.fromJson(Map<String, dynamic> json) {
    final mobilityCost =
        (json['mobility_cost_eur'] ?? json['fuel_cost_eur']) as num;
    return DetourDecision(
      isWorthIt: json['is_worth_it'] as bool,
      grossSavingsEur: (json['gross_savings_eur'] as num).toDouble(),
      mobilityCostEur: mobilityCost.toDouble(),
      fuelCostEur: (json['fuel_cost_eur'] as num).toDouble(),
      netSavingsEur: (json['net_savings_eur'] as num).toDouble(),
      explanation: json['explanation'] as String,
    );
  }
}

class UserProfile {
  final double lat;
  final double lng;
  final String transportMode;
  final String? fuelType;
  final double? consumptionPer100km;
  final double? energyPricePerUnit;
  final double? transitCostPerKmEur;
  final double? carryingCapacityKg;
  final double? maxReachableDistanceKm;

  UserProfile({
    required this.lat,
    required this.lng,
    required this.transportMode,
    this.fuelType,
    this.consumptionPer100km,
    this.energyPricePerUnit,
    this.transitCostPerKmEur,
    this.carryingCapacityKg,
    this.maxReachableDistanceKm,
  });

  Map<String, dynamic> toUserJson() {
    return {
      'location': {'lat': lat, 'lng': lng},
      'transport_mode': transportMode,
      if (fuelType != null) 'fuel_type': fuelType,
      if (consumptionPer100km != null)
        'vehicle_consumption_per_100km': consumptionPer100km,
      if (transitCostPerKmEur != null)
        'transit_cost_per_km_eur': transitCostPerKmEur,
      if (carryingCapacityKg != null) 'carrying_capacity_kg': carryingCapacityKg,
      if (maxReachableDistanceKm != null)
        'max_reachable_distance_km': maxReachableDistanceKm,
    };
  }

  Map<String, dynamic> toStorageJson() {
    return {
      'lat': lat,
      'lng': lng,
      'transport_mode': transportMode,
      'fuel_type': fuelType,
      'consumption_per_100km': consumptionPer100km,
      'energy_price_per_unit': energyPricePerUnit,
      'transit_cost_per_km_eur': transitCostPerKmEur,
      'carrying_capacity_kg': carryingCapacityKg,
      'max_reachable_distance_km': maxReachableDistanceKm,
    };
  }

  factory UserProfile.fromStorageJson(Map<String, dynamic> json) {
    return UserProfile(
      lat: (json['lat'] as num).toDouble(),
      lng: (json['lng'] as num).toDouble(),
      transportMode: json['transport_mode'] as String,
      fuelType: json['fuel_type'] as String?,
      consumptionPer100km: (json['consumption_per_100km'] as num?)?.toDouble(),
      energyPricePerUnit: (json['energy_price_per_unit'] as num?)?.toDouble(),
      transitCostPerKmEur:
          (json['transit_cost_per_km_eur'] as num?)?.toDouble(),
      carryingCapacityKg: (json['carrying_capacity_kg'] as num?)?.toDouble(),
      maxReachableDistanceKm:
          (json['max_reachable_distance_km'] as num?)?.toDouble(),
    );
  }

  UserProfile copyWith({
    double? lat,
    double? lng,
    String? transportMode,
    String? fuelType,
    double? consumptionPer100km,
    double? energyPricePerUnit,
    double? transitCostPerKmEur,
    double? carryingCapacityKg,
    double? maxReachableDistanceKm,
  }) {
    return UserProfile(
      lat: lat ?? this.lat,
      lng: lng ?? this.lng,
      transportMode: transportMode ?? this.transportMode,
      fuelType: fuelType ?? this.fuelType,
      consumptionPer100km: consumptionPer100km ?? this.consumptionPer100km,
      energyPricePerUnit: energyPricePerUnit ?? this.energyPricePerUnit,
      transitCostPerKmEur: transitCostPerKmEur ?? this.transitCostPerKmEur,
      carryingCapacityKg: carryingCapacityKg ?? this.carryingCapacityKg,
      maxReachableDistanceKm:
          maxReachableDistanceKm ?? this.maxReachableDistanceKm,
    );
  }
}

class ShoppingItem {
  final String name;
  final double quantity;
  final String unit;
  final String? preferredBrand;
  final String? category;
  final double? estimatedWeightKg;

  ShoppingItem({
    required this.name,
    required this.quantity,
    required this.unit,
    this.preferredBrand,
    this.category,
    this.estimatedWeightKg,
  });

  Map<String, dynamic> toJson() {
    return {
      'name': name,
      'quantity': quantity,
      'unit': unit,
      if (preferredBrand != null && preferredBrand!.isNotEmpty)
        'preferred_brand': preferredBrand,
      if (category != null && category!.isNotEmpty) 'category': category,
      if (estimatedWeightKg != null) 'estimated_weight_kg': estimatedWeightKg,
    };
  }
}

class RouteOption {
  final int rank;
  final String storeId;
  final String chain;
  final double distanceKm;
  final double basketTotalEur;
  final double mobilityCostEur;
  final double estimatedTotalEur;
  final double weightedScoreEur;

  RouteOption({
    required this.rank,
    required this.storeId,
    required this.chain,
    required this.distanceKm,
    required this.basketTotalEur,
    required this.mobilityCostEur,
    required this.estimatedTotalEur,
    required this.weightedScoreEur,
  });

  factory RouteOption.fromJson(Map<String, dynamic> json) {
    return RouteOption(
      rank: json['rank'] as int,
      storeId: json['store_id'] as String,
      chain: json['chain'] as String,
      distanceKm: (json['distance_km'] as num).toDouble(),
      basketTotalEur: (json['basket_total_eur'] as num).toDouble(),
      mobilityCostEur: (json['mobility_cost_eur'] as num).toDouble(),
      estimatedTotalEur: (json['estimated_total_eur'] as num).toDouble(),
      weightedScoreEur: (json['weighted_score_eur'] as num).toDouble(),
    );
  }
}

class MapPoint {
  final String storeId;
  final String chain;
  final double lat;
  final double lng;
  final double estimatedTotalEur;

  MapPoint({
    required this.storeId,
    required this.chain,
    required this.lat,
    required this.lng,
    required this.estimatedTotalEur,
  });

  factory MapPoint.fromJson(Map<String, dynamic> json) {
    final location = json['location'] as Map<String, dynamic>;
    return MapPoint(
      storeId: json['store_id'] as String,
      chain: json['chain'] as String,
      lat: (location['lat'] as num).toDouble(),
      lng: (location['lng'] as num).toDouble(),
      estimatedTotalEur: (json['estimated_total_eur'] as num).toDouble(),
    );
  }
}

class RoutePlanResult {
  final String recommendedStoreId;
  final String globalMinimumStoreId;
  final double estimatedTotalEur;
  final List<RouteOption> rankedOptions;
  final List<MapPoint> mapPoints;
  final Map<String, dynamic> debug;

  RoutePlanResult({
    required this.recommendedStoreId,
    required this.globalMinimumStoreId,
    required this.estimatedTotalEur,
    required this.rankedOptions,
    required this.mapPoints,
    required this.debug,
  });

  factory RoutePlanResult.fromJson(Map<String, dynamic> json) {
    final options = (json['ranked_options'] as List<dynamic>)
        .map((entry) => RouteOption.fromJson(entry as Map<String, dynamic>))
        .toList();
    final points = (json['map_points'] as List<dynamic>)
        .map((entry) => MapPoint.fromJson(entry as Map<String, dynamic>))
        .toList();

    return RoutePlanResult(
      recommendedStoreId: json['recommended_store_id'] as String,
      globalMinimumStoreId: json['global_minimum_store_id'] as String,
      estimatedTotalEur: (json['estimated_total_eur'] as num).toDouble(),
      rankedOptions: options,
      mapPoints: points,
      debug: (json['debug'] as Map<String, dynamic>?) ?? {},
    );
  }
}

class BrandSuggestion {
  final String itemName;
  final String preferredBrand;
  final String preferredChain;
  final double preferredTotalEur;
  final String alternativeBrand;
  final String alternativeChain;
  final double alternativeTotalEur;
  final double savingsEur;

  BrandSuggestion({
    required this.itemName,
    required this.preferredBrand,
    required this.preferredChain,
    required this.preferredTotalEur,
    required this.alternativeBrand,
    required this.alternativeChain,
    required this.alternativeTotalEur,
    required this.savingsEur,
  });

  factory BrandSuggestion.fromJson(Map<String, dynamic> json) {
    return BrandSuggestion(
      itemName: json['item_name'] as String,
      preferredBrand: json['preferred_brand'] as String,
      preferredChain: json['preferred_chain'] as String,
      preferredTotalEur: (json['preferred_total_eur'] as num).toDouble(),
      alternativeBrand: json['alternative_brand'] as String,
      alternativeChain: json['alternative_chain'] as String,
      alternativeTotalEur: (json['alternative_total_eur'] as num).toDouble(),
      savingsEur: (json['savings_eur'] as num).toDouble(),
    );
  }
}

class BrandAlternativeResult {
  final List<BrandSuggestion> suggestions;
  final double totalPotentialSavingsEur;

  BrandAlternativeResult({
    required this.suggestions,
    required this.totalPotentialSavingsEur,
  });

  factory BrandAlternativeResult.fromJson(Map<String, dynamic> json) {
    final suggestions = (json['suggestions'] as List<dynamic>)
        .map((entry) => BrandSuggestion.fromJson(entry as Map<String, dynamic>))
        .toList();
    return BrandAlternativeResult(
      suggestions: suggestions,
      totalPotentialSavingsEur:
          (json['total_potential_savings_eur'] as num).toDouble(),
    );
  }
}
