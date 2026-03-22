import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';
import 'models.dart';

void main() {
  runApp(const AInkaufApp());
}

class AInkaufApp extends StatefulWidget {
  const AInkaufApp({super.key});

  @override
  State<AInkaufApp> createState() => _AInkaufAppState();
}

class _AInkaufAppState extends State<AInkaufApp> {
  static const String profileKey = 'ainkauf_user_profile';
  final ApiClient api = ApiClient(baseUrl: 'http://localhost:8000');
  bool loading = true;
  UserProfile? profile;

  @override
  void initState() {
    super.initState();
    _loadProfile();
  }

  Future<void> _loadProfile() async {
    final prefs = await SharedPreferences.getInstance();
    final rawProfile = prefs.getString(profileKey);
    if (rawProfile != null) {
      final json = jsonDecode(rawProfile) as Map<String, dynamic>;
      profile = UserProfile.fromStorageJson(json);
    }
    if (mounted) {
      setState(() {
        loading = false;
      });
    }
  }

  Future<void> _saveProfile(UserProfile nextProfile) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(profileKey, jsonEncode(nextProfile.toStorageJson()));
    if (mounted) {
      setState(() {
        profile = nextProfile;
      });
    }
  }

  Future<void> _resetProfile() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(profileKey);
    if (mounted) {
      setState(() {
        profile = null;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AInkauf',
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.teal,
      ),
      home: loading
          ? const Scaffold(body: Center(child: CircularProgressIndicator()))
          : profile == null
              ? OnboardingScreen(
                  api: api,
                  onCompleted: _saveProfile,
                )
              : PlannerScreen(
                  api: api,
                  profile: profile!,
                  onProfileChanged: _saveProfile,
                  onResetOnboarding: _resetProfile,
                ),
    );
  }
}

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({
    super.key,
    required this.api,
    required this.onCompleted,
  });

  final ApiClient api;
  final Future<void> Function(UserProfile profile) onCompleted;

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final latController = TextEditingController(text: '48.2082');
  final lngController = TextEditingController(text: '16.3738');
  final consumptionController = TextEditingController(text: '6.5');
  final energyPriceController = TextEditingController(text: '1.70');
  final transitCostController = TextEditingController(text: '0.40');
  final carryingCapacityController = TextEditingController(text: '8');
  final maxReachController = TextEditingController(text: '2.5');

  String mode = 'car';
  String fuelType = 'benzin';
  String? error;
  bool saving = false;

  @override
  void dispose() {
    latController.dispose();
    lngController.dispose();
    consumptionController.dispose();
    energyPriceController.dispose();
    transitCostController.dispose();
    carryingCapacityController.dispose();
    maxReachController.dispose();
    super.dispose();
  }

  Future<void> _completeOnboarding() async {
    setState(() {
      saving = true;
      error = null;
    });
    try {
      final profile = UserProfile(
        lat: double.parse(latController.text),
        lng: double.parse(lngController.text),
        transportMode: mode,
        fuelType: mode == 'car' ? fuelType : null,
        consumptionPer100km:
            mode == 'car' ? double.parse(consumptionController.text) : null,
        energyPricePerUnit:
            mode == 'car' ? double.parse(energyPriceController.text) : null,
        transitCostPerKmEur:
            mode == 'transit' ? double.parse(transitCostController.text) : null,
        carryingCapacityKg: (mode == 'foot' || mode == 'bike')
            ? double.parse(carryingCapacityController.text)
            : null,
        maxReachableDistanceKm: (mode == 'foot' || mode == 'bike')
            ? double.parse(maxReachController.text)
            : null,
      );
      await widget.api.initializeOnboarding(profile);
      await widget.onCompleted(profile);
    } catch (e) {
      setState(() {
        error = e.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          saving = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Willkommen bei AInkauf')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text(
            'Beim ersten Start brauchen wir deinen Standort und deine Mobilitaet.',
            style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
          ),
          const SizedBox(height: 14),
          TextField(
            controller: latController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Breitengrad (Lat)'),
          ),
          TextField(
            controller: lngController,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(labelText: 'Laengengrad (Lng)'),
          ),
          const SizedBox(height: 8),
          DropdownButtonFormField<String>(
            initialValue: mode,
            decoration: const InputDecoration(labelText: 'Mobilitaetsvariante'),
            items: const [
              DropdownMenuItem(value: 'car', child: Text('Auto')),
              DropdownMenuItem(value: 'foot', child: Text('Zu Fuss')),
              DropdownMenuItem(value: 'bike', child: Text('Rad')),
              DropdownMenuItem(value: 'transit', child: Text('Oeffis')),
            ],
            onChanged: (value) {
              if (value == null) return;
              setState(() {
                mode = value;
                if (mode == 'foot') {
                  maxReachController.text = '2.5';
                  carryingCapacityController.text = '8';
                } else if (mode == 'bike') {
                  maxReachController.text = '8';
                  carryingCapacityController.text = '18';
                }
              });
            },
          ),
          if (mode == 'car') ...[
            DropdownButtonFormField<String>(
              initialValue: fuelType,
              decoration: const InputDecoration(labelText: 'Antriebsart'),
              items: const [
                DropdownMenuItem(value: 'benzin', child: Text('Benzin')),
                DropdownMenuItem(value: 'diesel', child: Text('Diesel')),
                DropdownMenuItem(value: 'autogas', child: Text('Autogas')),
                DropdownMenuItem(value: 'strom', child: Text('Strom')),
              ],
              onChanged: (value) {
                if (value == null) return;
                setState(() => fuelType = value);
              },
            ),
            TextField(
              controller: consumptionController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: fuelType == 'strom'
                    ? 'Verbrauch (kWh/100km)'
                    : 'Verbrauch (L/100km)',
              ),
            ),
            TextField(
              controller: energyPriceController,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(
                labelText: fuelType == 'strom'
                    ? 'Strompreis (EUR/kWh)'
                    : 'Spritpreis (EUR/L)',
              ),
            ),
          ],
          if (mode == 'transit')
            TextField(
              controller: transitCostController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Oeffi-Kosten EUR/km'),
            ),
          if (mode == 'foot' || mode == 'bike') ...[
            TextField(
              controller: carryingCapacityController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Traglast (kg)'),
            ),
            TextField(
              controller: maxReachController,
              keyboardType: TextInputType.number,
              decoration:
                  const InputDecoration(labelText: 'Max. erreichbare Distanz (km)'),
            ),
          ],
          const SizedBox(height: 18),
          FilledButton.icon(
            onPressed: saving ? null : _completeOnboarding,
            icon: const Icon(Icons.check_circle_outline),
            label: Text(saving ? 'Speichere...' : 'Onboarding abschliessen'),
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(error!, style: const TextStyle(color: Colors.red)),
            ),
        ],
      ),
    );
  }
}

enum SortMode { cheap, expensive, weighted }

class PlannerScreen extends StatefulWidget {
  const PlannerScreen({
    super.key,
    required this.api,
    required this.profile,
    required this.onProfileChanged,
    required this.onResetOnboarding,
  });

  final ApiClient api;
  final UserProfile profile;
  final Future<void> Function(UserProfile profile) onProfileChanged;
  final Future<void> Function() onResetOnboarding;

  @override
  State<PlannerScreen> createState() => _PlannerScreenState();
}

class _PlannerScreenState extends State<PlannerScreen> {
  final itemNameController = TextEditingController();
  final itemQuantityController = TextEditingController(text: '1');
  final itemUnitController = TextEditingController(text: 'stk');
  final itemBrandController = TextEditingController();
  final itemCategoryController = TextEditingController();
  final itemWeightController = TextEditingController();

  late UserProfile profile;
  final List<ShoppingItem> items = [];
  RoutePlanResult? routeResult;
  BrandAlternativeResult? alternatives;
  bool loading = false;
  String? error;
  SortMode sortMode = SortMode.weighted;

  @override
  void initState() {
    super.initState();
    profile = widget.profile;
  }

  @override
  void dispose() {
    itemNameController.dispose();
    itemQuantityController.dispose();
    itemUnitController.dispose();
    itemBrandController.dispose();
    itemCategoryController.dispose();
    itemWeightController.dispose();
    super.dispose();
  }

  Future<void> _switchMode(String mode) async {
    setState(() {
      final lat = profile.lat;
      final lng = profile.lng;
      if (mode == 'foot') {
        profile = UserProfile(
          lat: lat,
          lng: lng,
          transportMode: mode,
          carryingCapacityKg: profile.carryingCapacityKg ?? 8,
          maxReachableDistanceKm: profile.maxReachableDistanceKm ?? 2.5,
        );
      } else if (mode == 'bike') {
        profile = UserProfile(
          lat: lat,
          lng: lng,
          transportMode: mode,
          carryingCapacityKg: profile.carryingCapacityKg ?? 18,
          maxReachableDistanceKm: profile.maxReachableDistanceKm ?? 8,
        );
      } else if (mode == 'transit') {
        profile = UserProfile(
          lat: lat,
          lng: lng,
          transportMode: mode,
          transitCostPerKmEur: profile.transitCostPerKmEur ?? 0.4,
        );
      } else {
        profile = UserProfile(
          lat: lat,
          lng: lng,
          transportMode: mode,
          fuelType: profile.fuelType ?? 'benzin',
          consumptionPer100km: profile.consumptionPer100km ?? 6.5,
          energyPricePerUnit: profile.energyPricePerUnit ?? 1.7,
        );
      }
    });
    await widget.onProfileChanged(profile);
  }

  void _addItem() {
    if (itemNameController.text.trim().isEmpty) return;
    setState(() {
      items.add(
        ShoppingItem(
          name: itemNameController.text.trim(),
          quantity: double.tryParse(itemQuantityController.text) ?? 1,
          unit: itemUnitController.text.trim().isEmpty
              ? 'stk'
              : itemUnitController.text.trim(),
          preferredBrand: itemBrandController.text.trim().isEmpty
              ? null
              : itemBrandController.text.trim(),
          category: itemCategoryController.text.trim().isEmpty
              ? null
              : itemCategoryController.text.trim(),
          estimatedWeightKg: itemWeightController.text.trim().isEmpty
              ? null
              : double.tryParse(itemWeightController.text.trim()),
        ),
      );
      itemNameController.clear();
      itemQuantityController.text = '1';
      itemUnitController.text = 'stk';
      itemBrandController.clear();
      itemCategoryController.clear();
      itemWeightController.clear();
    });
  }

  Future<void> _runOptimization() async {
    if (items.isEmpty) {
      setState(() {
        error = 'Bitte mindestens 1 Artikel eingeben.';
      });
      return;
    }
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final optimized = await widget.api.optimizeShopping(
        profile: profile,
        shoppingItems: items,
      );
      final brandSuggestions = await widget.api.getBrandAlternatives(
        shoppingItems: items,
      );
      setState(() {
        routeResult = optimized;
        alternatives = brandSuggestions;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
      });
    } finally {
      if (mounted) {
        setState(() {
          loading = false;
        });
      }
    }
  }

  List<RouteOption> _sortedOptions() {
    final options = [...?routeResult?.rankedOptions];
    if (sortMode == SortMode.cheap) {
      options.sort((a, b) => a.estimatedTotalEur.compareTo(b.estimatedTotalEur));
    } else if (sortMode == SortMode.expensive) {
      options.sort((a, b) => b.estimatedTotalEur.compareTo(a.estimatedTotalEur));
    } else {
      options.sort((a, b) => a.weightedScoreEur.compareTo(b.weightedScoreEur));
    }
    return options;
  }

  Set<Marker> _markers() {
    final mapPoints = routeResult?.mapPoints ?? [];
    final markers = <Marker>{
      Marker(
        markerId: const MarkerId('user'),
        position: LatLng(profile.lat, profile.lng),
        infoWindow: const InfoWindow(title: 'Dein Standort'),
        icon: BitmapDescriptor.defaultMarkerWithHue(BitmapDescriptor.hueAzure),
      ),
    };
    for (final point in mapPoints) {
      markers.add(
        Marker(
          markerId: MarkerId(point.storeId),
          position: LatLng(point.lat, point.lng),
          infoWindow: InfoWindow(
            title: point.chain,
            snippet: 'Total: ${point.estimatedTotalEur.toStringAsFixed(2)} EUR',
          ),
        ),
      );
    }
    return markers;
  }

  Widget _buildMapSection() {
    if (kIsWeb) {
      return Container(
        height: 260,
        decoration: BoxDecoration(
          color: Colors.teal.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: Colors.teal.withValues(alpha: 0.25)),
        ),
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Kartenansicht (Web-Fallback)',
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 6),
            const Text(
              'Falls Google Maps im Browser nicht verfuegbar ist, werden die Marktpunkte hier als Liste angezeigt.',
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView(
                children: (routeResult?.mapPoints ?? [])
                    .map(
                      (point) => ListTile(
                        dense: true,
                        contentPadding: EdgeInsets.zero,
                        title: Text(point.chain),
                        subtitle: Text(
                          '(${point.lat.toStringAsFixed(4)}, ${point.lng.toStringAsFixed(4)})',
                        ),
                        trailing: Text(
                          '${point.estimatedTotalEur.toStringAsFixed(2)} EUR',
                        ),
                      ),
                    )
                    .toList(),
              ),
            ),
          ],
        ),
      );
    }

    return SizedBox(
      height: 260,
      child: ClipRRect(
        borderRadius: BorderRadius.circular(16),
        child: GoogleMap(
          initialCameraPosition: CameraPosition(
            target: LatLng(profile.lat, profile.lng),
            zoom: 12.5,
          ),
          markers: _markers(),
        ),
      ),
    );
  }

  Widget _buildResultSection() {
    if (routeResult == null) return const SizedBox.shrink();
    final options = _sortedOptions();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 14),
        Text(
          'Empfehlung: ${routeResult!.recommendedStoreId} '
          '(~${routeResult!.estimatedTotalEur.toStringAsFixed(2)} EUR)',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 10),
        _buildMapSection(),
        const SizedBox(height: 10),
        SegmentedButton<SortMode>(
          segments: const [
            ButtonSegment(value: SortMode.weighted, label: Text('Gewichtet')),
            ButtonSegment(value: SortMode.cheap, label: Text('Guenstig')),
            ButtonSegment(value: SortMode.expensive, label: Text('Teuer')),
          ],
          selected: {sortMode},
          onSelectionChanged: (selection) {
            setState(() {
              sortMode = selection.first;
            });
          },
        ),
        const SizedBox(height: 10),
        ...options.map(
          (option) => Card(
            child: ListTile(
              title: Text('${option.rank}. ${option.chain}'),
              subtitle: Text(
                'Distanz ${option.distanceKm.toStringAsFixed(1)} km | '
                'Warenkorb ${option.basketTotalEur.toStringAsFixed(2)} EUR | '
                'Mobilitaet ${option.mobilityCostEur.toStringAsFixed(2)} EUR',
              ),
              trailing: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Text(
                    '${option.estimatedTotalEur.toStringAsFixed(2)} EUR',
                    style: const TextStyle(fontWeight: FontWeight.bold),
                  ),
                  Text('Score ${option.weightedScoreEur.toStringAsFixed(2)}'),
                ],
              ),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildAlternativeSection() {
    final data = alternatives;
    if (data == null) return const SizedBox.shrink();
    if (data.suggestions.isEmpty) {
      return const Padding(
        padding: EdgeInsets.only(top: 8),
        child: Text('Keine guenstigeren Marken-Alternativen gefunden.'),
      );
    }
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const SizedBox(height: 14),
        Text(
          'Marken-Alternativen: Potenzial '
          '${data.totalPotentialSavingsEur.toStringAsFixed(2)} EUR',
          style: const TextStyle(fontWeight: FontWeight.bold),
        ),
        const SizedBox(height: 8),
        ...data.suggestions.map(
          (suggestion) => Card(
            child: ListTile(
              title: Text(suggestion.itemName),
              subtitle: Text(
                '${suggestion.preferredBrand} (${suggestion.preferredChain}) '
                '-> ${suggestion.alternativeBrand} (${suggestion.alternativeChain})',
              ),
              trailing: Text(
                '-${suggestion.savingsEur.toStringAsFixed(2)} EUR',
                style: const TextStyle(
                  color: Colors.green,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AInkauf Planer'),
        actions: [
          IconButton(
            tooltip: 'Onboarding zuruecksetzen',
            icon: const Icon(Icons.restart_alt),
            onPressed: widget.onResetOnboarding,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Mobilitaet',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  DropdownButtonFormField<String>(
                    initialValue: profile.transportMode,
                    decoration:
                        const InputDecoration(labelText: 'Transportmodus'),
                    items: const [
                      DropdownMenuItem(value: 'car', child: Text('Auto')),
                      DropdownMenuItem(value: 'foot', child: Text('Zu Fuss')),
                      DropdownMenuItem(value: 'bike', child: Text('Rad')),
                      DropdownMenuItem(value: 'transit', child: Text('Oeffis')),
                    ],
                    onChanged: (value) {
                      if (value == null) return;
                      _switchMode(value);
                    },
                  ),
                  if (profile.transportMode == 'foot' ||
                      profile.transportMode == 'bike')
                    Text(
                      'Reichweite: ${(profile.maxReachableDistanceKm ?? 0).toStringAsFixed(1)} km | '
                      'Traglast: ${(profile.carryingCapacityKg ?? 0).toStringAsFixed(1)} kg',
                    ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Einkaufsliste',
                    style: TextStyle(fontWeight: FontWeight.bold),
                  ),
                  TextField(
                    controller: itemNameController,
                    decoration: const InputDecoration(labelText: 'Artikel'),
                  ),
                  Row(
                    children: [
                      Expanded(
                        child: TextField(
                          controller: itemQuantityController,
                          keyboardType: TextInputType.number,
                          decoration:
                              const InputDecoration(labelText: 'Menge'),
                        ),
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: TextField(
                          controller: itemUnitController,
                          decoration: const InputDecoration(labelText: 'Einheit'),
                        ),
                      ),
                    ],
                  ),
                  TextField(
                    controller: itemBrandController,
                    decoration: const InputDecoration(
                      labelText: 'Bevorzugte Marke (optional)',
                    ),
                  ),
                  TextField(
                    controller: itemCategoryController,
                    decoration:
                        const InputDecoration(labelText: 'Kategorie (optional)'),
                  ),
                  TextField(
                    controller: itemWeightController,
                    keyboardType: TextInputType.number,
                    decoration: const InputDecoration(
                      labelText: 'Geschaetztes Gewicht in kg (optional)',
                    ),
                  ),
                  const SizedBox(height: 8),
                  FilledButton.icon(
                    onPressed: _addItem,
                    icon: const Icon(Icons.add),
                    label: const Text('Artikel hinzufuegen'),
                  ),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: items
                        .map(
                          (item) => InputChip(
                            label: Text('${item.quantity} ${item.unit} ${item.name}'),
                            onDeleted: () {
                              setState(() {
                                items.remove(item);
                              });
                            },
                          ),
                        )
                        .toList(),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 10),
          FilledButton.icon(
            onPressed: loading ? null : _runOptimization,
            icon: const Icon(Icons.route),
            label: Text(
              loading ? 'Optimiere...' : 'Optimierung starten',
            ),
          ),
          if (error != null)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(error!, style: const TextStyle(color: Colors.red)),
            ),
          _buildAlternativeSection(),
          _buildResultSection(),
        ],
      ),
    );
  }
}
