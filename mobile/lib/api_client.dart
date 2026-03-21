import 'dart:convert';

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiClient {
  ApiClient({required this.baseUrl});

  final String baseUrl;

  Future<ParsedItem> parseItem(String text) async {
    final response = await http.post(
      Uri.parse('$baseUrl/nlp/parse-item'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'text': text}),
    );

    if (response.statusCode >= 400) {
      throw Exception('Parse failed: ${response.body}');
    }

    return ParsedItem.fromJson(jsonDecode(response.body) as Map<String, dynamic>);
  }

  Future<DetourDecision> evaluateDetour({
    required double baseStoreTotal,
    required double candidateStoreTotal,
    required double detourDistanceKm,
    required UserProfile profile,
  }) async {
    final payload = {
      'base_store_total_eur': baseStoreTotal,
      'candidate_store_total_eur': candidateStoreTotal,
      'detour_distance_km': detourDistanceKm,
      if (profile.energyPricePerUnit != null)
        'energy_price_eur_per_unit': profile.energyPricePerUnit,
      'user': profile.toUserJson(),
    };

    final response = await http.post(
      Uri.parse('$baseUrl/optimization/detour-worth-it'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );

    if (response.statusCode >= 400) {
      throw Exception('Detour check failed: ${response.body}');
    }

    return DetourDecision.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<void> initializeOnboarding(UserProfile profile) async {
    final response = await http.post(
      Uri.parse('$baseUrl/onboarding/initialize'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode({'user': profile.toUserJson()}),
    );

    if (response.statusCode >= 400) {
      throw Exception('Onboarding failed: ${response.body}');
    }
  }

  Future<RoutePlanResult> optimizeShopping({
    required UserProfile profile,
    required List<ShoppingItem> shoppingItems,
  }) async {
    final quantitySum = shoppingItems.fold<double>(
      0,
      (sum, item) => sum + item.quantity,
    );
    final baseBasket = 8 + (quantitySum * 1.4);

    final stores = [
      {
        'store_id': 'spar-1010',
        'chain': 'Spar',
        'location': {'lat': profile.lat + 0.004, 'lng': profile.lng + 0.003},
        'basket_total_eur': (baseBasket * 1.00),
        'missing_items': 0,
      },
      {
        'store_id': 'billa-1020',
        'chain': 'Billa',
        'location': {'lat': profile.lat + 0.006, 'lng': profile.lng - 0.004},
        'basket_total_eur': (baseBasket * 1.04),
        'missing_items': 0,
      },
      {
        'store_id': 'hofer-1040',
        'chain': 'Hofer',
        'location': {'lat': profile.lat + 0.018, 'lng': profile.lng + 0.012},
        'basket_total_eur': (baseBasket * 0.90),
        'missing_items': 0,
      },
      {
        'store_id': 'lidl-1050',
        'chain': 'Lidl',
        'location': {'lat': profile.lat + 0.011, 'lng': profile.lng - 0.01},
        'basket_total_eur': (baseBasket * 0.94),
        'missing_items': 0,
      },
    ];

    final payload = {
      'shopping_list': shoppingItems.map((item) => item.toJson()).toList(),
      'user': profile.toUserJson(),
      if (profile.energyPricePerUnit != null)
        'energy_price_eur_per_unit': profile.energyPricePerUnit,
      'distance_weight_eur_per_km': 0.09,
      'stores': stores,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/optimization/calculate-optimal-route'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (response.statusCode >= 400) {
      throw Exception('Optimization failed: ${response.body}');
    }
    return RoutePlanResult.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }

  Future<BrandAlternativeResult> getBrandAlternatives({
    required List<ShoppingItem> shoppingItems,
  }) async {
    final offers = <Map<String, dynamic>>[];
    for (final item in shoppingItems) {
      final category = item.category ?? 'Sonstiges';
      if (item.preferredBrand != null && item.preferredBrand!.isNotEmpty) {
        offers.add({
          'store_id': 'billa-1020',
          'chain': 'Billa',
          'product_name': item.name,
          'brand': item.preferredBrand,
          'category': category,
          'unit': item.unit,
          'price_eur': 2.20,
          'is_brand_product': true,
        });
      }
      offers.add({
        'store_id': 'hofer-1040',
        'chain': 'Hofer',
        'product_name': item.name,
        'brand': 'Eigenmarke',
        'category': category,
        'unit': item.unit,
        'price_eur': 1.55,
      });
    }

    final payload = {
      'shopping_list': shoppingItems.map((item) => item.toJson()).toList(),
      'offers': offers,
    };

    final response = await http.post(
      Uri.parse('$baseUrl/optimization/brand-alternatives'),
      headers: {'Content-Type': 'application/json'},
      body: jsonEncode(payload),
    );
    if (response.statusCode >= 400) {
      throw Exception('Alternative check failed: ${response.body}');
    }
    return BrandAlternativeResult.fromJson(
      jsonDecode(response.body) as Map<String, dynamic>,
    );
  }
}
