# AInkauf - Agent Instructions

## Cursor Cloud specific instructions

### Overview
AInkauf is a grocery shopping optimizer for Austrian consumers. It has a **Python/FastAPI backend** and a **Flutter mobile app**. The backend provides NLP item parsing, detour cost-benefit analysis, and optimal route calculation.

### Services

| Service | How to run | Port |
|---------|-----------|------|
| PostgreSQL + PostGIS | `docker compose up -d db` | 5432 |
| FastAPI backend (Docker) | `docker compose up -d --build api` | 8000 |
| FastAPI backend (local) | `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload` | 8000 |

### Running tests
```bash
cd backend && source .venv/bin/activate && pytest -q
```
Tests are pure unit tests and do **not** require the database or Docker.

### Linting
```bash
cd backend && source .venv/bin/activate && ruff check .
```

### Key caveats
- Docker must be started manually: `sudo dockerd &>/tmp/dockerd.log &` — wait ~5 seconds before running `docker compose` commands.
- After starting Docker, you may need `sudo chmod 666 /var/run/docker.sock` for non-root access.
- The backend venv lives at `backend/.venv`. Always activate it before running `pytest`, `uvicorn`, or `ruff`.
- The `GOOGLE_MAPS_API_KEY` env var is optional; the backend falls back to haversine distance calculation without it.
- Swagger docs are at `http://localhost:8000/docs` when the API is running.
- Flutter mobile app setup is documented in the README but requires Flutter SDK which is outside the standard backend dev workflow.
