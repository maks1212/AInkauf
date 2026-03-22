# API Research for Real Austrian Data

This document tracks real and candidate APIs for AInkauf.

## 1) Fuel prices (Austria) - Real production source

### E-Control Sprit API
- Base docs: `https://api.e-control.at/sprit/1.0/doc/index.html`
- OpenAPI JSON: `https://api.e-control.at/sprit/1.0/api-docs?group=public-api`
- Search endpoint used by backend:
  - `GET https://api.e-control.at/sprit/1.0/search/gas-stations/by-address`
  - params: `fuelType` (`DIE`, `SUP`, `GAS`), `latitude`, `longitude`, `includeClosed`

Status:
- Integrated in backend as live provider (`EControlFuelProvider`).

Limitations:
- No EV charging prices in this API (strom must be user-provided or via separate EV provider).

## 2) Grocery prices (Austria) - Real source currently integrated

### Heisse-Preise canonical datasets
- Site: `https://heisse-preise.io/`
- Data pattern used:
  - `https://heisse-preise.io/data/latest-canonical.<store>.compressed.json`
  - examples: `billa`, `spar`, `lidl`

Status:
- Integrated in backend as live provider (`HeisspreiseLiveProvider`).

Limitations:
- Data freshness differs by chain; some chains have reduced or stopped updates at times.
- Product matching still needs stronger normalization (EAN/GTIN, pack conversion) for production-grade basket totals.

## 3) Candidate grocery augmentation APIs

### OpenFoodFacts Open Prices
- Docs: `https://prices.openfoodfacts.org/api/docs`
- Type: crowdsourced receipt/product prices

Use case:
- Fallback enrichment for products/chains with sparse updates.
- Good for metadata coverage; quality depends on crowd submissions.

Status:
- Not integrated yet (tracked as candidate source).

## 4) Recommendation for production setup

1. Keep E-Control as primary fuel source.
2. Keep Heisse-Preise as primary grocery source for Austrian chains.
3. Add a product identity layer (EAN/GTIN + unit normalization) before route optimization.
4. Add EV charging API if `strom` should be fully live.
