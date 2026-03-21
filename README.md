# AInkauf

Die erste Einkaufsliste, die mitdenkt: Preise vergleichen, Spritkosten einrechnen und wirtschaftlich sinnvolle Einkaufsentscheidungen treffen.

## Tech Stack

- **Mobile App:** Flutter (Android + iOS)
- **Backend API:** FastAPI (Python)
- **Datenbank:** PostgreSQL + PostGIS
- **Routen:** Google Maps Distance Matrix API (MVP-Connector vorbereitet)

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
│   │   │   └── austria_price_provider.py
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
K = (D / 100) * Verbrauch * Spritpreis
Netto = (Preis_Basisladen - Preis_Alternativladen) - K
```

Wenn `Netto < 0`, dann ist der Umweg nicht wirtschaftlich.

### 2) Gesamt-Route optimieren
Endpoint: `POST /optimization/calculate-optimal-route`

- Findet den globalen Preis-Minimum-Store
- Berücksichtigt Zusatzdistanz gegenüber dem nächstgelegenen vollständigen Store
- Schließt Stores aus, falls Netto-Ersparnis negativ ist

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
    "fuel_price_eur_per_liter": 1.70,
    "user": {
      "location": {"lat": 48.2082, "lng": 16.3738},
      "vehicle_consumption_l_per_100km": 6.5,
      "fuel_type": "benzin"
    }
  }'
```
