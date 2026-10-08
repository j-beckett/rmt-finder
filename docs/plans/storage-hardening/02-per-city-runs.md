# Implementation plan — Slice 2: per-city runs

Decisions: `docs/plans/storage-hardening/decisions.md` (items 1, 5, 8, 9).
Builds on slice 1 (`01-migration-foundation.md`). No frontend change.

## Goal

A scrape run belongs to one city. Each scheduler cycle scrapes the cities
one after another and records one run per city, so a failed Vancouver scrape
can never hide a good Victoria run. The API serves one city at a time,
defaulting to Victoria so the live frontend is unaffected.

## Files to touch

- `backend/storage.py`
  - Migration 2 (appended, never editing migration 1):
    - `ALTER TABLE scrape_runs ADD COLUMN city TEXT NOT NULL DEFAULT 'victoria'`
      (existing rows are backfilled by the default; the default stays in
      place as a safety net).
    - `idx_scrape_runs_city_id` on `scrape_runs(city, id)` — the
      "latest run for a city" lookups.
    - `idx_slots_city_start_at` on `slots(city, start_at)` and
      `idx_slots_run_id` on `slots(run_id)`.
  - `RunRecord.city`.
  - `record_run(city, started_at, ...)`: `city` is required, no default.
  - `latest_run(city)` and `latest_good_run(city)` filter on city.
- `backend/scraper/clinics.py`: `cities(clinics)` — sorted distinct
  lowercase cities; `clinics_in_city(clinics, city)`.
- `backend/config.py`: `timezone_for_city` becomes case-insensitive (clinic
  cities are lowercase, the table keys are not).
- `backend/main.py`: `scrape_city(city)` (the old body, parameterised);
  `main()` loops all cities for the local CLI.
- `backend/scheduler.py`: `run_once(city, scrape)`, `run_cycle(scrape,
  cities)`, `run_forever` loops cycles. Failure isolation per city. A
  comment at the loop states why it is sequential and points at the
  parallel plan in `decisions.md`.
- `backend/api.py`: `?city=` defaults to Victoria, lowercased; unknown city
  → 404; runs read per city; `clinics_total` and `timezone` per city; the
  post-hoc slot filter goes (a run's slots are all one city now).
- Tests: updated for the new signatures; see sequence below.
- `docs/plans/storage-hardening/decisions.md`: no change needed.

## Out of scope

Retention, discovery cache, frontend city dropdown, per-city intervals.

## TDD sequence (one red/green cycle each)

1. Migration 2 adds `scrape_runs.city`; a run recorded before the migration
   reads back as `'victoria'`.
2. Migration 2 creates the three indexes.
3. `record_run` takes and persists a `city`.
4. `record_run` without a city raises `TypeError` (guard; written after 3, so
   it cannot be seen red — the parameter is simply required).
5. `latest_run(city)` returns the newest attempt for that city only.
6. `latest_good_run(city)` returns that city's latest good run and slots; a
   newer failed run in another city does not affect it.
7. `cities()` / `clinics_in_city()` helpers; `timezone_for_city` is
   case-insensitive.
8. `main.scrape_city(city)` scrapes only that city and records a run with
   that city; `main.main()` scrapes every city.
9. `scheduler.run_once(city, scrape)`: a raising scrape records a
   zero-success run **for that city** and does not propagate.
10. `scheduler.run_cycle`: scrapes cities in order; one city raising does
    not stop the next.
11. `scheduler.run_forever` runs cycles with the interval between them.
12. API: no `city` → Victoria's run; `?city=` is case-insensitive and picks
    that city's run (replaces the old slot-filter test).
13. API: unknown city → 404.
14. API: `clinics_total` counts only that city's clinics; `timezone` is the
    city's.
15. Version assertions in existing tests use `len(MIGRATIONS)` instead of a
    hard-coded 1 (refactor, not a behaviour change).

## Risks

- **The deploy order matters.** `deploy.sh` runs `migrate.py` before the
  restart, so the old API/scheduler keep running against a database that
  already has the `city` column for a moment. That is safe: the old code
  never selects or inserts `scrape_runs.city`, and the column has a default.
- **Backfill assumption.** Every existing run is labelled `'victoria'`. True
  today (every clinic in `CLINICS` is Victoria) — verify with the checklist
  query on the real data before deploying.
- **Case.** `cities()` returns lowercase and the API lowercases its input.
  A clinic configured with a capitalised city would still match, because
  `run_all` already compares case-insensitively and `cities()` lowercases.

## Manual checklist (for the user, before committing)

1. `venv\Scripts\python.exe -m pytest` passes.
2. On a copy of the real database: `SELECT DISTINCT city FROM slots;`
   returns only `victoria` (confirms the backfill assumption).
3. Run `migrate.py` on that copy: `PRAGMA user_version` is 2,
   `SELECT DISTINCT city FROM scrape_runs;` returns `victoria`, and the three
   indexes exist (`SELECT name FROM sqlite_master WHERE type='index';`).
4. Start the API against the migrated copy: `/api/availability` and
   `/api/availability?city=Victoria` return the same data;
   `/api/availability?city=atlantis` returns 404.
5. Run `python main.py` from `backend\` on a fresh DB path: one run is
   recorded with `city = 'victoria'`.
6. Skim the scheduler loop comment about sequential scraping.
