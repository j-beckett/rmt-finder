# Implementation plan — Availability API

Issue: `docs/plans/vertical-slice/02-availability-api.md`
PRD: `docs/prd/vertical-slice.md`

## Files to touch

- `backend/api.py` (new) — FastAPI app, the only new module:
  - `GET /api/availability` — reads via `Storage` only (dependency creates
    `Storage(config.db_path())` per request, so tests can point the env var
    at a temp DB).
  - Response envelope:
    - `scraped_at` — served run's `finished_at` (null when DB has no good run)
    - `latest_attempt_at` — latest run's `finished_at` regardless of success
    - `clinics_attempted` — served run's attempted count
    - `failed_clinics` — served run's failed clinic names
    - `slots` — served run's slots, fields mirroring `AvailabilityResult`
  - Serving rule: `storage.latest_good_run()` already skips newer
    zero-success runs, so the fallback is a storage read, not API logic;
    `storage.latest_run()` supplies `latest_attempt_at`.
  - `?city=` query param — cosmetic case-insensitive filter on slot city.
  - CORS middleware allowing the frontend dev origin, env var
    `RMT_FINDER_FRONTEND_ORIGIN`, default `http://localhost:5173`.
  - No POST routes, no auth, no pagination.
- `backend/config.py` — add `frontend_origin()`.
- `requirements.txt` — add fastapi, uvicorn, httpx (TestClient dependency).

## Run command

`venv\Scripts\python.exe -m uvicorn api:app --app-dir backend`

## TDD sequence (one red/green cycle each)

1. Normal case: populated temp DB → 200 with the latest good run's slots.
2. Envelope contents: scraped_at, latest_attempt_at, clinics_attempted,
   failed_clinics.
3. Fallback: newer zero-success run → serves prior good run's slots and
   `latest_attempt_at` > `scraped_at`.
4. Empty-but-successful run → empty slot list, normal envelope
   (`latest_attempt_at == scraped_at`).
5. Empty DB → 200, empty slots, null timestamps (frontend's "broken" state).
6. `?city=` filters slots case-insensitively; unknown city → empty list.
7. CORS: preflight/request from the frontend dev origin is allowed.
8. `config.frontend_origin()` honors env var, defaults sensibly.
