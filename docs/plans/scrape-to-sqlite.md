# Implementation plan — Scrape-to-SQLite pipeline

Issue: `docs/plans/vertical-slice/01-scrape-to-sqlite.md`
PRD: `docs/prd/vertical-slice.md`

## Files to touch

- `backend/scraper/models.py` — add `RunResult` dataclass (slots + attempted /
  succeeded / failed clinic-name lists) and `RunRecord` (a persisted
  `scrape_runs` row read back from storage).
- `backend/scraper/runner.py` — `run_all` returns `RunResult` instead of a
  flat slot list; accepts injectable `clinics` / `adapters` for tests.
- `backend/storage.py` (new) — owns ALL DB access:
  - `Storage(db_path)` — connects, creates parent dir, initializes schema
    (`scrape_runs`, `slots` per PRD Storage section).
  - `record_run(started_at, finished_at, attempted, succeeded, failed) -> run_id`
  - `insert_slots(run_id, slots: list[AvailabilityResult])`
  - `latest_good_run() -> (RunRecord, list[AvailabilityResult]) | None` —
    latest run with `clinics_succeeded > 0` (this IS the zero-success
    fallback: a failed latest run is skipped over).
  - `latest_run() -> RunRecord | None` — latest attempt regardless of
    success, for the API envelope's "latest attempt" timestamp.
- `backend/config.py` — `db_path()` reading `RMT_FINDER_DB_PATH`, default
  `data/rmt-finder.db`.
- `backend/main.py` — run all clinics once, write snapshot via storage,
  print run summary (run id, clinics scraped, failures, slot count). JSON
  dump removed.

## Schema

- `scrape_runs(id INTEGER PK, started_at TEXT, finished_at TEXT,
  clinics_attempted INTEGER, clinics_succeeded INTEGER,
  failed_clinics TEXT /* JSON array of clinic names */)`
- `slots(id INTEGER PK, run_id INTEGER FK->scrape_runs, clinic_name, city,
  platform, rmt_name, service_type, treatment_name, duration_minutes,
  start_at, booking_url)`
- Append-only: INSERTs only, no UPDATE/DELETE anywhere.

## TDD sequence (one red/green cycle each)

1. `Storage(tmp)` creates both tables.
2. `record_run` returns an id and persists all run fields.
3. Reruns append: two `record_run` calls → two rows, distinct ids.
4. `insert_slots` + `latest_good_run` round-trips slot fields.
5. `latest_good_run` skips a newer zero-success run (fallback).
6. `latest_good_run` returns `None` on an empty DB.
7. `latest_run` returns the newest attempt even when it failed.
8. `config.db_path()` honors env var, defaults sensibly.
9. `run_all` returns per-clinic outcomes (stub adapters: one succeeds, one
   raises).
10. CLI `main()` writes one run + slots via storage, prints summary, writes
    no JSON file.
