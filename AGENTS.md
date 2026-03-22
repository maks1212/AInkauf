# AInkauf - Agent Instructions

## Cursor Cloud specific instructions

### Overview
AInkauf is a grocery shopping optimizer for Austrian consumers. It has a **Python/FastAPI backend**, an **Angular frontend** (with NgRx SignalStore + Auth0), and a **Flutter mobile app**. The backend provides NLP item parsing, detour cost-benefit analysis, and optimal route calculation.

### Services

| Service | How to run | Port |
|---------|-----------|------|
| PostgreSQL + PostGIS | `docker compose up -d db` | 5432 |
| FastAPI backend (Docker) | `docker compose up -d --build api` | 8000 |
| FastAPI backend (local) | `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload` | 8000 |
| Angular frontend | `cd frontend && npx ng serve` | 4200 |

### Running tests
```bash
# Backend (pure unit tests, no DB required)
cd backend && source .venv/bin/activate && pytest -q

# Frontend build check
cd frontend && npx ng build
```

### Linting
```bash
# Backend
cd backend && source .venv/bin/activate && ruff check .

# Frontend
cd frontend && npx ng lint
```

### Frontend architecture (Signal Onion)
The Angular frontend follows an **onion architecture** with NgRx **SignalStore**:
- `core/models/` — Domain models (innermost, no Angular deps)
- `core/ports/` — Abstract API port (`AInkaufApiPort`)
- `infrastructure/api/` — Concrete HTTP implementation
- `application/stores/` — NgRx SignalStore stores (NLP, Detour, Route, Price)
- `presentation/` — Components and pages (outermost)

Auth0 login is pre-integrated but bypassed in dev mode (when `environment.auth0.domain` is placeholder). Set real Auth0 credentials in `frontend/src/environments/environment.ts` to enable login.

### Key caveats
- Docker must be started manually: `sudo dockerd &>/tmp/dockerd.log &` — wait ~5 seconds before running `docker compose` commands.
- After starting Docker, you may need `sudo chmod 666 /var/run/docker.sock` for non-root access.
- The backend venv lives at `backend/.venv`. Always activate it before running `pytest`, `uvicorn`, or `ruff`.
- The backend includes CORS middleware allowing `http://localhost:4200` (Angular dev server).
- The `GOOGLE_MAPS_API_KEY` env var is optional; the backend falls back to haversine distance calculation without it.
- Swagger docs are at `http://localhost:8000/docs` when the API is running.
- Flutter mobile app setup is documented in the README but requires Flutter SDK which is outside the standard backend dev workflow.
