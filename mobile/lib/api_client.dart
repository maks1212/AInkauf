import 'dart:convert';
import 'dart:math' as math;

import 'package:http/http.dart' as http;

import 'models.dart';

class ApiClient {
  ApiClient({required this.baseUrl});

  final String baseUrl;
  List<Map<String, dynamic>> _lastLiveRecords = [];

  static const Set<String> _brandTokenIgnore = {
    'billa',
    'spar',
    'lidl',
    'hofer',
    'bio',
    'und',
    'der',
    'die',
    'das',
  };

  static const Map<String, List<String>> _storeSearchKeys = {
    'billa': ['billa'],
    'spar': ['spar'],
    'lidl': ['lidl'],
    'hofer': ['hofer'],
  };

  static const Map<String, Map<String, double>> _storeOffsets = {
    'billa': {'lat': 0.006, 'lng': -0.004},
    'spar': {'lat': 0.004, 'lng': 0.003},
    'lidl': {'lat': 0.011, 'lng': -0.010},
    'hofer': {'lat': 0.018, 'lng': 0.012},
  };

  String _normalizeText(String value) {
    return value.trim().toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), ' ');
  }

  List<String> _searchTermsFromItems(List<ShoppingItem> items) {
    final terms = <String>{};
    for (final item in items) {
      final normalized = _normalizeText(item.name);
      for (final token in normalized.split(' ')) {
        if (token.length >= 3) {
          terms.add(token);
        }
      }
    }
    return terms.toList();
  }

  ({String unitFamily, double quantity}) _toBaseQuantity(double value, String unit) {
    final normalizedUnit = unit.trim().toLowerCase();
    if (normalizedUnit == 'g') {
      return (unitFamily: 'mass', quantity: value / 1000.0);
    }
    if (normalizedUnit == 'kg') {
      return (unitFamily: 'mass', quantity: value);
    }
    if (normalizedUnit == 'ml') {
      return (unitFamily: 'volume', quantity: value / 1000.0);
    }
    if (normalizedUnit == 'l') {
      return (unitFamily: 'volume', quantity: value);
    }
    if (normalizedUnit == 'stk' ||
        normalizedUnit == 'stueck' ||
        normalizedUnit == 'stück' ||
        normalizedUnit == 'pack' ||
        normalizedUnit == 'paket') {
      return (unitFamily: 'count', quantity: value);
    }
    return (unitFamily: 'unknown', quantity: value);
  }

  bool _recordMatchesItem(Map<String, dynamic> record, ShoppingItem item) {
    final key = _normalizeText(record['product_key'] as String? ?? '');
    final itemTokens = _normalizeText(item.name)
        .split(' ')
        .where((token) => token.length >= 3)
        .toList();
    if (itemTokens.isEmpty) {
      return key.contains(_normalizeText(item.name));
    }
    return itemTokens.any((token) => key.contains(token));
  }

  double _lineTotalFromRecord(Map<String, dynamic> record, ShoppingItem item) {
    final price = (record['price_eur'] as num).toDouble();
    final packageUnit =
        (record['package_unit'] as String?)?.trim().toLowerCase() ?? item.unit;
    final packageQuantity = ((record['package_quantity'] as num?)?.toDouble() ?? 1.0)
        .clamp(0.0001, 1000000)
        .toDouble();

    final requested = _toBaseQuantity(item.quantity, item.unit);
    final package = _toBaseQuantity(packageQuantity, packageUnit);

    if (requested.unitFamily == package.unitFamily &&
        requested.unitFamily != 'unknown') {
      final ratio = requested.quantity / math.max(package.quantity, 0.0001);
      final packagesNeeded = math.max(1, ratio.ceil());
      return price * packagesNeeded;
    }

    final fallbackQuantity = _toBaseQuantity(item.quantity, item.unit).quantity;
    return price * math.max(1, fallbackQuantity);
  }

  Future<List<Map<String, dynamic>>> _fetchLivePriceRecords(
    List<ShoppingItem> shoppingItems,
  ) async {
    final searchTerms = _searchTermsFromItems(shoppingItems);
    final query = <String, String>{
      'stores': 'billa,spar,lidl,hofer',
      'limit': '5000',
      if (searchTerms.isNotEmpty) 'search': searchTerms.join(','),
    };
    final uri = Uri.parse('$baseUrl/providers/austria-prices').replace(
      queryParameters: query,
    );
    final response = await http.get(uri);
    if (response.statusCode >= 400) {
      throw Exception('Live price fetch failed: ${response.body}');
    }
    final payload = jsonDecode(response.body) as Map<String, dynamic>;
    final parsed = (payload['items'] as List<dynamic>)
        .map((entry) => entry as Map<String, dynamic>)
        .toList();
    _lastLiveRecords = parsed;
    return parsed;
  }

  String? _extractBrandCandidateFromProductKey(String productKey) {
    final normalized = _normalizeText(productKey)
        .replaceAll('ä', 'ae')
        .replaceAll('ö', 'oe')
        .replaceAll('ü', 'ue')
        .replaceAll('ß', 'ss');
    final tokens =
        normalized.split(' ').where((token) => token.trim().isNotEmpty).toList();
    for (final token in tokens) {
      if (token.length < 3) continue;
      if (RegExp(r'^\d+$').hasMatch(token)) continue;
      if (_brandTokenIgnore.contains(token)) continue;
      return token[0].toUpperCase() + token.substring(1);
    }
    return null;
  }

  Future<List<String>> fetchBrandSuggestions(String productQuery) async {
    final query = productQuery.trim();
    if (query.length < 2) return const [];

    final uri = Uri.parse('$baseUrl/providers/austria-prices').replace(
      queryParameters: {
        'stores': 'billa,spar,lidl',
        'search': query,
        'limit': '600',
      },
    );

    try {
      final response = await http.get(uri);
      if (response.statusCode >= 400) {
        return const [];
      }
      final payload = jsonDecode(response.body) as Map<String, dynamic>;
      final items = (payload['items'] as List<dynamic>)
          .map((entry) => entry as Map<String, dynamic>)
          .toList();

      final suggestions = <String>{};
      for (final item in items) {
        final candidate = _extractBrandCandidateFromProductKey(
          item['product_key'] as String? ?? '',
        );
        if (candidate != null) {
          suggestions.add(candidate);
        }
      }
      return suggestions.take(30).toList();
    } catch (_) {
      return const [];
    }
  }

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
    final records = await _fetchLivePriceRecords(shoppingItems);
    if (records.isEmpty) {
      throw Exception('Keine Live-Preisdaten fuer die Einkaufsliste gefunden.');
    }

    final stores = <Map<String, dynamic>>[];
    for (final entry in _storeSearchKeys.entries) {
      final storeKey = entry.key;
      final chainName =
          '${storeKey[0].toUpperCase()}${storeKey.substring(1).toLowerCase()}';
      final offsets = _storeOffsets[storeKey]!;
      final storeRecords = records.where((record) {
        final storeId = (record['store_id'] as String? ?? '').toLowerCase();
        return entry.value.any((needle) => storeId.contains(needle));
      }).toList();

      double basketTotal = 0;
      int missingItems = 0;
      for (final item in shoppingItems) {
        final candidates = storeRecords
            .where((record) => _recordMatchesItem(record, item))
            .toList();
        if (candidates.isEmpty) {
          missingItems += 1;
          continue;
        }
        candidates.sort(
          (a, b) => (a['price_eur'] as num).compareTo(b['price_eur'] as num),
        );
        basketTotal += _lineTotalFromRecord(candidates.first, item);
      }

      stores.add({
        'store_id': '$storeKey-live',
        'chain': chainName,
        'location': {
          'lat': profile.lat + offsets['lat']!,
          'lng': profile.lng + offsets['lng']!,
        },
        'basket_total_eur': basketTotal,
        'missing_items': missingItems,
      });
    }

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

  List<ShoppingChecklistEntry> buildShoppingChecklist({
    required List<ShoppingItem> shoppingItems,
    required RoutePlanResult routePlan,
  }) {
    final records = _lastLiveRecords;
    if (records.isEmpty) return [];

    String optionStoreKey(RouteOption option) {
      final key = option.storeId.toLowerCase();
      if (!key.contains('-')) return key;
      return key.split('-').first;
    }

    final optionsByDistance = [...routePlan.rankedOptions]
      ..sort((a, b) => a.distanceKm.compareTo(b.distanceKm));
    final createdAt = DateTime.now();
    final checklist = <ShoppingChecklistEntry>[];

    for (var index = 0; index < shoppingItems.length; index++) {
      final item = shoppingItems[index];
      RouteOption? selectedOption;
      double? selectedLineTotal;

      for (final option in optionsByDistance) {
        final storeKey = optionStoreKey(option);
        final storeRecords = records.where((record) {
          final storeId = (record['store_id'] as String? ?? '').toLowerCase();
          return storeId.contains(storeKey);
        }).toList();
        final candidates =
            storeRecords.where((record) => _recordMatchesItem(record, item)).toList();
        if (candidates.isEmpty) {
          continue;
        }
        candidates.sort(
          (a, b) => (a['price_eur'] as num).compareTo(b['price_eur'] as num),
        );
        final lineTotal = _lineTotalFromRecord(candidates.first, item);
        if (selectedLineTotal == null || lineTotal < selectedLineTotal) {
          selectedOption = option;
          selectedLineTotal = lineTotal;
        }
      }

      if (selectedOption == null || selectedLineTotal == null) {
        continue;
      }

      checklist.add(
        ShoppingChecklistEntry(
          id: 'task-${createdAt.millisecondsSinceEpoch}-$index',
          itemName: item.name,
          quantityLabel: '${item.quantity} ${item.unit}',
          storeId: selectedOption.storeId,
          storeChain: selectedOption.chain,
          storeDistanceKm: selectedOption.distanceKm,
          estimatedLineTotalEur: selectedLineTotal,
          createdAt: createdAt,
        ),
      );
    }

    checklist.sort((a, b) {
      final byDistance = a.storeDistanceKm.compareTo(b.storeDistanceKm);
      if (byDistance != 0) return byDistance;
      return a.storeChain.compareTo(b.storeChain);
    });
    return checklist;
  }

  Future<BrandAlternativeResult> getBrandAlternatives({
    required List<ShoppingItem> shoppingItems,
  }) async {
    final liveRecords = await _fetchLivePriceRecords(shoppingItems);
    final offers = <Map<String, dynamic>>[];
    for (final record in liveRecords) {
      final storeId = (record['store_id'] as String?) ?? 'unknown';
      final chain = storeId.split('-').first;
      final productKey = (record['product_key'] as String?) ?? '';
      final productName = productKey.replaceAll('_', ' ');
      final tokens = _normalizeText(productName).split(' ');
      final extractedBrand = tokens.isNotEmpty ? tokens.first : 'unknown';
      final packageUnit = (record['package_unit'] as String?) ?? 'stk';

      offers.add({
        'store_id': storeId,
        'chain': chain.isEmpty
            ? 'Unknown'
            : '${chain[0].toUpperCase()}${chain.substring(1)}',
        'product_name': productName,
        'brand': extractedBrand,
        'category': 'Sonstiges',
        'unit': packageUnit,
        'price_eur': record['price_eur'],
        'is_brand_product': true,
      });
    }

    final payload = {
      'shopping_list': shoppingItems.map((item) => item.toJson()).toList(),
      'offers': offers,
      'prefer_no_name': true,
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
