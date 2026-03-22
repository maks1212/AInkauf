import 'package:flutter/material.dart';

import 'api_client.dart';
import 'models.dart';

void main() {
  runApp(const AInkaufApp());
}

class AInkaufApp extends StatelessWidget {
  const AInkaufApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AInkauf',
      theme: ThemeData(colorSchemeSeed: Colors.green, useMaterial3: true),
      home: const HomeScreen(),
    );
  }
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final ApiClient api = ApiClient(baseUrl: 'http://localhost:8000');

  final TextEditingController parseController =
      TextEditingController(text: '3kg Aepfel');
  final TextEditingController baseTotalController =
      TextEditingController(text: '42.90');
  final TextEditingController candidateTotalController =
      TextEditingController(text: '41.99');
  final TextEditingController distanceController =
      TextEditingController(text: '5');
  final TextEditingController consumptionController =
      TextEditingController(text: '6.5');
  final TextEditingController energyPriceController =
      TextEditingController(text: '1.70');
  final TextEditingController transitCostController =
      TextEditingController(text: '0.40');

  String selectedTransportMode = 'car';
  String selectedFuelType = 'benzin';

  ParsedItem? parsedItem;
  DetourDecision? detourDecision;
  String? error;

  @override
  void dispose() {
    parseController.dispose();
    baseTotalController.dispose();
    candidateTotalController.dispose();
    distanceController.dispose();
    consumptionController.dispose();
    energyPriceController.dispose();
    transitCostController.dispose();
    super.dispose();
  }

  Future<void> parseItem() async {
    try {
      final result = await api.parseItem(parseController.text.trim());
      setState(() {
        parsedItem = result;
        error = null;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
      });
    }
  }

  Future<void> evaluateDetour() async {
    try {
      final result = await api.evaluateDetour(
        baseStoreTotal: double.parse(baseTotalController.text),
        candidateStoreTotal: double.parse(candidateTotalController.text),
        detourDistanceKm: double.parse(distanceController.text),
        transportMode: selectedTransportMode,
        consumptionPer100km: selectedTransportMode == 'car'
            ? double.parse(consumptionController.text)
            : null,
        fuelType: selectedTransportMode == 'car' ? selectedFuelType : null,
        energyPricePerUnit: selectedTransportMode == 'car'
            ? double.parse(energyPriceController.text)
            : null,
        transitCostPerKmEur: selectedTransportMode == 'transit'
            ? double.parse(transitCostController.text)
            : null,
      );
      setState(() {
        detourDecision = result;
        error = null;
      });
    } catch (e) {
      setState(() {
        error = e.toString();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('AInkauf MVP')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'NLP-Parser',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            TextField(
              controller: parseController,
              decoration:
                  const InputDecoration(labelText: 'Freitext, z.B. 3kg Aepfel'),
            ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: parseItem,
              child: const Text('Parsen'),
            ),
            if (parsedItem != null)
              Text(
                'Erkannt: ${parsedItem!.quantity} ${parsedItem!.unit} ${parsedItem!.productName}',
              ),
            const Divider(height: 32),
            const Text(
              '5-km-Umweg-Wirtschaftlichkeit',
              style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
            ),
            TextField(
              controller: baseTotalController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Preis Basisladen'),
            ),
            TextField(
              controller: candidateTotalController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Preis Alternativladen'),
            ),
            TextField(
              controller: distanceController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(labelText: 'Umweg in km'),
            ),
            DropdownButtonFormField<String>(
              value: selectedTransportMode,
              decoration:
                  const InputDecoration(labelText: 'Transportmodus'),
              items: const [
                DropdownMenuItem(value: 'car', child: Text('Auto')),
                DropdownMenuItem(value: 'foot', child: Text('Zu Fuß')),
                DropdownMenuItem(value: 'bike', child: Text('Rad')),
                DropdownMenuItem(value: 'transit', child: Text('Oeffis')),
              ],
              onChanged: (value) {
                if (value == null) return;
                setState(() => selectedTransportMode = value);
              },
            ),
            if (selectedTransportMode == 'car') ...[
              DropdownButtonFormField<String>(
                value: selectedFuelType,
                decoration: const InputDecoration(labelText: 'Antriebsart'),
                items: const [
                  DropdownMenuItem(value: 'benzin', child: Text('Benzin')),
                  DropdownMenuItem(value: 'diesel', child: Text('Diesel')),
                  DropdownMenuItem(value: 'autogas', child: Text('Autogas')),
                  DropdownMenuItem(value: 'strom', child: Text('Strom')),
                ],
                onChanged: (value) {
                  if (value == null) return;
                  setState(() => selectedFuelType = value);
                },
              ),
              TextField(
                controller: consumptionController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: selectedFuelType == 'strom'
                      ? 'Verbrauch (kWh/100km)'
                      : 'Verbrauch (L/100km)',
                ),
              ),
              TextField(
                controller: energyPriceController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: selectedFuelType == 'strom'
                      ? 'Strompreis (EUR/kWh)'
                      : 'Spritpreis (EUR/Liter)',
                ),
              ),
            ],
            if (selectedTransportMode == 'transit')
              TextField(
                controller: transitCostController,
                keyboardType: TextInputType.number,
                decoration:
                    const InputDecoration(labelText: 'Oeffi-Kosten (EUR/km)'),
              ),
            const SizedBox(height: 8),
            FilledButton(
              onPressed: evaluateDetour,
              child: const Text('Berechnen'),
            ),
            if (detourDecision != null)
              Card(
                margin: const EdgeInsets.only(top: 12),
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        detourDecision!.isWorthIt
                            ? 'Sinnvoll'
                            : 'Nicht sinnvoll',
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      Text(
                        'Brutto-Ersparnis: ${detourDecision!.grossSavingsEur.toStringAsFixed(2)} EUR',
                      ),
                      Text(
                        'Mobilitaetskosten: ${detourDecision!.mobilityCostEur.toStringAsFixed(2)} EUR',
                      ),
                      Text(
                        'Netto-Ersparnis: ${detourDecision!.netSavingsEur.toStringAsFixed(2)} EUR',
                      ),
                      Text(detourDecision!.explanation),
                    ],
                  ),
                ),
              ),
            if (error != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  error!,
                  style: const TextStyle(color: Colors.red),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
