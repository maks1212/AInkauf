# AInkauf Price Intelligence API (DDD, unabhaengig)

Dieses Dokument beschreibt eine saubere, unabhaengige Architektur fuer eine eigene Preis-API auf Basis von Crawling/Scraping-Quellen.
Ziel: Preise pro Supermarkt, Produkt, Marke und Aktionen inkl. Gueltigkeitszeitraum (`valid_from`, `valid_to`) fuer die eigene Web-App.

---

## 0) Rechtlicher Rahmen (wichtig vor Technik)

Bevor eine Quelle gescraped wird, muss pro Quelle geprueft werden:

1. Nutzungsbedingungen / Lizenz
2. robots.txt / API-Richtlinien
3. Urheberrecht / Datenbankschutz
4. Erlaubnis fuer kommerzielle Nutzung (falls relevant)

Empfehlung:
- Bevorzugt offizielle APIs/Feeds oder vertraglich freigegebene Datenquellen.
- Scraping nur dort, wo es rechtlich und technisch ausdruecklich zulaessig ist.
- Pro Quelle ein "Compliance-Profil" pflegen (siehe Bounded Context `Source Governance`).

---

## 1) Zielbild

Wir bauen eine **eigene, unabhaengige Price-Intelligence-API** als gekapselten Service:

- liest Rohdaten aus mehreren Quellen (Crawler/Scraper/API/Feed),
- normalisiert auf ein kanonisches Produkt-/Marktmodell,
- versioniert Preise und Aktionen zeitlich,
- liefert schnelle Query-Endpunkte fuer die AInkauf Web-App.

Die bestehende AInkauf-App konsumiert dann nur noch diese interne API.

---

## 2) Oesterreich Supermarkt-Katalog (Startumfang)

Prioritaet fuer Vielfalt + Datenrelevanz:

### Tier 1 (hohe Relevanz)
- BILLA
- SPAR
- HOFER
- LIDL
- PENNY
- MPREIS

### Tier 2 (regionale/erg. Abdeckung)
- UNIMARKT
- Nah&Frisch
- ADEG
- INTERSPAR / EUROSPAR (falls als eigene Banner ausgewertet)
- BIPA / DM / MUELLER (Drogerie als optionales Segment)

### Tier 3 (spaeter / online optional)
- Gurkerl
- Metro
- ausgewaehlte Online-Shops mit klaren Konditionen

Hinweis:
- "Chain" (Kette) und "Banner" (Markenauftritt) getrennt modellieren.
- "Store" immer als eigene Filiale mit Adresse + Geokoordinaten.

---

## 3) DDD Bounded Contexts

## 3.1 Source Governance Context
Verantwortung:
- Quelleninventar
- Lizenz/ToS/robots Bewertung
- technische Abrufregeln (rate limit, crawl window, headers)

Aggregate:
- `DataSource`
- `DataSourcePolicy`
- `SourceAccessCredential`

Wichtige Felder:
- `source_code`
- `source_type` (api, feed, scrape)
- `allowed_use` (private, research, commercial)
- `terms_url`, `robots_url`
- `scrape_allowed` (boolean + juristische Notiz)
- `max_requests_per_minute`
- `active`

## 3.2 Ingestion Context
Verantwortung:
- Abruf orchestration (scheduler + jobs)
- rohe Artefakte speichern
- idempotente Runs

Aggregate:
- `IngestionJob`
- `IngestionRun`
- `RawSnapshot`

## 3.3 Extraction & Normalization Context
Verantwortung:
- Parsing von Rohdaten
- Einheiten normalisieren
- Produktabgleich (Matching)
- Qualitätsmetrik je Match

Aggregate:
- `ParsedOffer`
- `ProductMatch`
- `NormalizationRule`

## 3.4 Master Data Context
Verantwortung:
- kanonische Stammdaten
- Produkt, Brand, Kategorie, Packungslogik
- Store/Filiale

Aggregate:
- `CanonicalProduct`
- `Brand`
- `Chain`
- `Store`

## 3.5 Price & Promotion Timeline Context
Verantwortung:
- zeitliche Historie von Preisen/Aktionen
- Gueltigkeitszeiträume
- Konfliktaufloesung bei mehreren Quellen

Aggregate:
- `PriceObservation`
- `PromotionObservation`
- `StoreAssortmentPresence`

## 3.6 Query API Context
Verantwortung:
- API fuer Frontend/Optimizer
- schnelle, cache-faehige Abfragen
- read-models / materialized views

---

## 4) Architektur (entkoppelt, "eigenstaendige API")

Empfohlen: Modular Monolith als Start, spaeter service-faehig.

```text
[Scheduler] -> [Ingestion Workers] -> [Raw Store]
                              -> [Parser/Normalizer] -> [Core DB]
                                                     -> [Search Index optional]

[AInkauf Web App] -> [Price Intelligence Query API] -> [Core DB + Read Models]
```

Technische Schichten (DDD):
- Domain (Entities, Value Objects, Domain Services)
- Application (Use Cases, Commands/Queries)
- Infrastructure (Scraper clients, DB, queue, http)
- Interface (REST endpoints)

---

## 5) Was vom Scraper gespeichert werden muss

Minimum pro Quelle/Run:

1. **Run-Metadaten**
   - `run_id`, `source_code`, `started_at`, `finished_at`, `status`, `error_count`
2. **Rohartefakt**
   - `raw_payload` (json/html)
   - `raw_hash` (dedup)
   - `fetched_at`
   - `source_url`
3. **Extrahiertes Angebot**
   - `source_product_id` (falls vorhanden)
   - `source_product_name`
   - `source_brand`
   - `source_package_qty`, `source_package_unit`
   - `source_price`
   - `currency`
   - `store_external_id` / `store_name`
4. **Kanonisierung**
   - `canonical_product_id`
   - `match_confidence` (0..1)
   - `match_strategy` (ean, exact, fuzzy)
5. **Preis-Zeitachse**
   - `price_amount`
   - `price_type` (regular, promo)
   - `valid_from`
   - `valid_to`
   - `observed_at`
   - `is_current`
6. **Aktionsdetails**
   - `promotion_type` (percent, amount_off, bundle, buy_x_get_y)
   - `promotion_text`
   - `min_qty`
   - `loyalty_required`
   - `valid_from`, `valid_to`
7. **Qualitaet/Audit**
   - `parse_version`
   - `normalization_version`
   - `quality_flags` (missing_unit, suspicious_price, etc.)

---

## 6) Datenmodell (SQL-Blueprint)

Beispieltabellen (zusaetzlich zum bestehenden MVP-Schema):

- `data_source`
- `data_source_policy`
- `ingestion_job`
- `ingestion_run`
- `raw_snapshot`
- `chain`
- `store`
- `brand`
- `canonical_product`
- `source_product_mapping`
- `price_observation`
- `promotion_observation`
- `store_product_presence`

Kernfelder fuer Gueltigkeit:

- `price_observation.valid_from TIMESTAMPTZ NOT NULL`
- `price_observation.valid_to TIMESTAMPTZ NULL`
- `promotion_observation.valid_from TIMESTAMPTZ NOT NULL`
- `promotion_observation.valid_to TIMESTAMPTZ NOT NULL`
- `observed_at TIMESTAMPTZ NOT NULL`

Regel:
- `valid_to IS NULL` bedeutet "aktuell offen", bis naechster Datensatz die Periode schliesst.

---

## 7) API-Design (Price Intelligence API)

Beispielendpunkte:

### Stammdaten
- `GET /v1/chains`
- `GET /v1/stores?chain=billa&lat=...&lng=...&radius_km=...`
- `GET /v1/products/search?q=gouda`

### Preise
- `GET /v1/prices/current?store_id=...&product_id=...`
- `GET /v1/prices/history?store_id=...&product_id=...&from=...&to=...`
- `POST /v1/basket/quote` (Liste Produkte -> Gesamtpreis je Store)

### Aktionen
- `GET /v1/promotions/current?store_id=...`
- `GET /v1/promotions/product?product_id=...&from=...&to=...`

### Ingestion intern/ops
- `POST /v1/admin/ingestion/run`
- `GET /v1/admin/ingestion/runs`
- `GET /v1/admin/data-quality`

---

## 8) Domainregeln (wichtig)

1. Preisdatum ohne Einheit darf nicht "trusted" sein.
2. Ein neuer Preis fuer gleiches Produkt+Store schliesst die offene Periode des alten Preises.
3. Promotion darf Preis nicht negativ machen.
4. Mapping mit niedriger Match-Confidence nur als "candidate", nicht fuer Optimierung verwenden.
5. Query API liest nur aus validierten Read Models.

---

## 9) Datenqualitaet und Monitoring

Metriken:
- scrape_success_rate
- parse_success_rate
- unmatched_product_ratio
- stale_price_ratio (z. B. > 7 Tage ohne Update)
- invalid_promotion_window_ratio (`valid_to < valid_from`)

Alerts:
- Quelle ohne Updates
- ploetzliche Preis-Ausreisser
- starker Einbruch in Produktabdeckung

---

## 10) Security, Betrieb, Skalierung

- Source-Credentials in Secret Store
- Rate-Limits pro Quelle strikt
- Queue-basierte Ingestion (retry + dead-letter)
- Idempotenz via `raw_hash + source + fetched_at_bucket`
- Read cache fuer haeufige Basket-Quotes
- Data retention:
  - raw snapshots kurz/mittel
  - normalized observations langfristig fuer Historienanalyse

---

## 11) Empfohlene Einfuehrung in 3 Schritten

1. **MVP Service**
   - Tier-1 Chains
   - current prices + basic promotions
   - basket quote endpoint

2. **Quality Layer**
   - product matching confidence
   - anomaly detection
   - history endpoints

3. **Scale & Contracts**
   - weitere Ketten
   - vertragliche Datenquellen
   - SLA + robuste monitoring pipelines

---

## 12) Abgrenzung zur bestehenden AInkauf-API

Bestehende AInkauf-API:
- business logic (Optimierung, Mobilitaet, UI-Flows)

Neue Price Intelligence API:
- Datenbeschaffung, Normalisierung, Historie, Preis-/Aktionsabfragen

Damit bleibt die Kern-App stabil und die Datenplattform kann unabhaengig skaliert werden.

