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
    required String transportMode,
    double? consumptionPer100km,
    String? fuelType,
    double? energyPricePerUnit,
    double? transitCostPerKmEur,
  }) async {
    final payload = {
      'base_store_total_eur': baseStoreTotal,
      'candidate_store_total_eur': candidateStoreTotal,
      'detour_distance_km': detourDistanceKm,
      if (energyPricePerUnit != null)
        'energy_price_eur_per_unit': energyPricePerUnit,
      'user': {
        'location': {'lat': 48.2082, 'lng': 16.3738},
        'transport_mode': transportMode,
        if (consumptionPer100km != null)
          'vehicle_consumption_per_100km': consumptionPer100km,
        if (fuelType != null) 'fuel_type': fuelType,
        if (transitCostPerKmEur != null)
          'transit_cost_per_km_eur': transitCostPerKmEur,
      },
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
}
