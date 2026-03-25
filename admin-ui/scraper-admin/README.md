# Scraper Admin Angular Frontend

Angular frontend for the scraper administration APIs served by the FastAPI backend.

## Features

- Feature-first structure aligned with DDD layers:
  - `core/` (API clients + shared models)
  - `features/scraper-admin/application` (resource store/state orchestration)
  - `features/scraper-admin/ui` (Tailwind-based views)
- Covers core admin workflows:
  - start scraper jobs
  - update scheduler config
  - bootstrap persistence
  - catalog create/delete
  - offers list/filter/paginate/update/delete
  - reviews list/filter/paginate/resolve
- Auto-refresh while jobs are in `running` state.

## Run locally

```bash
npm install
npm start
```

Open:

- Frontend: `http://localhost:4200`
- Backend API expected at: `http://localhost:8000`

If your backend runs elsewhere, update `baseUrl` in:

- `src/app/core/api/scraper-admin-api.service.ts`

## Build

```bash
npm run build
```

## Test

```bash
npm run test -- --watch=false
```
