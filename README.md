# AInkauf

Die erste Einkaufsliste, die mitdenkt: Preise vergleichen, Mobilitaetskosten einrechnen, Marken-Alternativen vorschlagen und wirtschaftlich sinnvolle Einkaufsentscheidungen treffen.

## Tech Stack

- **Mobile App:** Flutter (Android + iOS)
- **Backend API:** FastAPI (Python)
- **Datenbank:** PostgreSQL + PostGIS
- **Routen:** Google Maps Distance Matrix API (MVP-Connector vorbereitet)
- **API Research:** `docs/API_RESEARCH.md`

## Projektstruktur

```text
.
├── backend
│   ├── app
│   │   ├── algorithm.py
│   │   ├── config.py
│   │   ├── distance_matrix.py
│   │   ├── main.py
│   │   ├── models.py
│   │   ├── nlp.py
│   │   ├── providers
│   │   │   ├── austria_price_provider.py
│   │   │   └── fuel_provider.py
│   │   └── schemas.py
│   ├── sql
│   │   └── schema.sql
│   ├── tests
│   └── requirements.txt
├── mobile
│   ├── lib
│   │   ├── api_client.dart
│   │   ├── main.dart
│   │   └── models.dart
│   └── pubspec.yaml
└── docker-compose.yml
```

## Datenmodell (MVP)

Siehe `backend/sql/schema.sql`:
- `app_user`
- `product`
- `store`
- `store_product_price` (tagesaktuelle Preise)
- `fuel_price`
- `shopping_list`
- `shopping_list_item`

## Kernlogik

### 1) 5-km-Umweg prüfen
Endpoint: `POST /optimization/detour-worth-it`

Formel:

```text
Auto: K = (D / 100) * Verbrauch * Energiepreis
Rad/Fuß: K = 0
Öffis: K = D * Oeffi_Kosten_pro_km
Netto = (Preis_Basisladen - Preis_Alternativladen) - K
```

Wenn `Netto < 0`, dann ist der Umweg nicht wirtschaftlich.

Unterstuetzte Antriebsarten im Auto-Modus:
- `diesel`
- `benzin`
- `autogas`
- `strom` (mit Verbrauch in kWh/100km und Preis in EUR/kWh)

Unterstuetzte Transportmodi:
- `car`
- `foot`
- `bike`
- `transit`

### 2) Gesamt-Route optimieren
Endpoint: `POST /optimization/calculate-optimal-route`

- Findet den globalen Preis-Minimum-Store
- Berücksichtigt Zusatzdistanz gegenüber dem nächstgelegenen vollständigen Store
- Schließt Stores aus, falls Netto-Ersparnis negativ ist
- Filtert bei `foot`/`bike` nach erreichbarer Distanz
- Berücksichtigt Traglast-Limit bei `foot`/`bike`
- Liefert `ranked_options` (gewichteter Score aus Preis + Distanz)
- Liefert `map_points` fuer eine Kartenvisualisierung

### 3) Marken-Alternativen und Ersparnis
Endpoint: `POST /optimization/brand-alternatives`

- Wenn ein Artikel `preferred_brand` hat, sucht die API guenstigere Alternativen
- Antwort enthaelt konkrete Vorschlaege pro Artikel plus `total_potential_savings_eur`
- No-Name-Prio pro Kette (wenn verfuegbar):
  - Spar -> `s-budget`
  - Billa -> `clever`
  - Hofer -> Eigenmarken (z. B. milfina/milsani/rio d'oro)
  - Lidl -> Eigenmarken (z. B. milbona/combino/cien/w5)

### 4) Erststart-Onboarding
Endpoint: `POST /onboarding/initialize`

- validiert Standort und Mobilitaetsvariante
- legt sinnvolle Default-Werte fuer Fuss-/Rad-Reichweite und Traglast fest

### 5) Live-Datenquellen (Österreich)
- **Supermarktpreise (real):** heisse-preise.io Canonical-Datasets
  - Endpoint: `GET /providers/austria-prices`
  - Optional: `stores=billa,spar,lidl`
- **Spritpreise (real):** E-Control Public API
  - Endpoint: `GET /providers/fuel-price-live?lat=...&lng=...&fuel_type=diesel`
- **API-Katalog fuer Research/Integrationen:**
  - Endpoint: `GET /providers/catalog`

Hinweis:
- Es gibt **keinen Mock-Fallback** mehr fuer diesen Endpoint: wenn die Live-Quelle nicht verfuegbar ist, liefert die API einen Fehler.
- Die Demo-Storeliste in der mobilen Optimierungsanfrage wird aktuell noch synthetisch erzeugt; fuer Produktion sollte sie aus den Live-Produktdaten gebaut werden.

## Backend starten

### Option A: Docker Compose

```bash
docker compose up --build
```

API danach unter `http://localhost:8000`.

### Option B: Lokal mit Python

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Tests

```bash
cd backend
pytest -q
```

## Flutter App starten

```bash
cd mobile
flutter pub get
flutter run
```

Hinweis: In `mobile/lib/main.dart` ist die API-Base-URL aktuell auf `http://localhost:8000` gesetzt.

## Beispiel-Requests

### NLP

```bash
curl -X POST http://localhost:8000/nlp/parse-item \
  -H "Content-Type: application/json" \
  -d '{"text":"3kg Aepfel"}'
```

### Detour-Check

```bash
curl -X POST http://localhost:8000/optimization/detour-worth-it \
  -H "Content-Type: application/json" \
  -d '{
    "base_store_total_eur": 42.90,
    "candidate_store_total_eur": 41.99,
    "detour_distance_km": 5,
    "energy_price_eur_per_unit": 1.70,
    "user": {
      "location": {"lat": 48.2082, "lng": 16.3738},
      "transport_mode": "car",
      "vehicle_consumption_per_100km": 6.5,
      "fuel_type": "benzin"
    }
  }'
```

### Detour-Check (kostenloser Modus: Rad/Fuß)

```bash
curl -X POST http://localhost:8000/optimization/detour-worth-it \
  -H "Content-Type: application/json" \
  -d '{
    "base_store_total_eur": 42.90,
    "candidate_store_total_eur": 42.40,
    "detour_distance_km": 5,
    "user": {
      "location": {"lat": 48.2082, "lng": 16.3738},
      "transport_mode": "bike"
    }
  }'
```

### Route-Optimierung mit Fuss-/Rad-Einschraenkung

```bash
curl -X POST http://localhost:8000/optimization/calculate-optimal-route \
  -H "Content-Type: application/json" \
  -d '{
    "shopping_list": [
      {"name":"Wasser", "quantity": 4, "unit":"l", "estimated_weight_kg": 4.0}
    ],
    "user": {
      "location": {"lat": 48.2082, "lng": 16.3738},
      "transport_mode": "foot",
      "max_reachable_distance_km": 2.0,
      "carrying_capacity_kg": 6.0
    },
    "stores": [
      {
        "store_id":"spar-1010",
        "chain":"Spar",
        "location":{"lat":48.214, "lng":16.376},
        "basket_total_eur": 9.5,
        "missing_items": 0
      }
    ]
  }'
```

### Live-Fuel-Preis von E-Control

```bash
curl "http://localhost:8000/providers/fuel-price-live?lat=48.2082&lng=16.3738&fuel_type=diesel"
```

### Live-Supermarktpreise (Heisse-Preise)

```bash
curl "http://localhost:8000/providers/austria-prices?stores=billa,spar&limit=20"
```

### Provider-Katalog (Research)

```bash
curl "http://localhost:8000/providers/catalog"
```
