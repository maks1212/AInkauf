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
  final TextEditingController fuelPriceController =
      TextEditingController(text: '1.70');

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
    fuelPriceController.dispose();
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
        consumptionLPer100km: double.parse(consumptionController.text),
        fuelType: 'benzin',
        fuelPricePerLiter: double.parse(fuelPriceController.text),
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
            TextField(
              controller: consumptionController,
              keyboardType: TextInputType.number,
              decoration:
                  const InputDecoration(labelText: 'Verbrauch (L/100km)'),
            ),
            TextField(
              controller: fuelPriceController,
              keyboardType: TextInputType.number,
              decoration:
                  const InputDecoration(labelText: 'Spritpreis (EUR/Liter)'),
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
                        'Spritkosten: ${detourDecision!.fuelCostEur.toStringAsFixed(2)} EUR',
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
