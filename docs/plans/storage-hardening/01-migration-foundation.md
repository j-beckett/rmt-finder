# Implementation plan — Slice 1: migration foundation

Decisions: `docs/plans/storage-hardening/decisions.md` (items 2, 3, 4).
No PRD / issue doc — backend-only hardening, no user-visible change.

## Goal

Give `Storage` a real schema-versioning mechanism and tidy its connection
handling, so later slices (per-city runs, retention, discovery cache) can
change the schema safely. Behaviour users see is identical.

## Files to touch

- `backend/storage.py`
  - `MIGRATIONS`: ordered list; each entry is a list of SQL statements.
    Entry 1 = the current schema, kept `IF NOT EXISTS` so an existing
    production DB (tables present, `user_version` 0) simply lands on v1.
  - `Storage.__init__` no longer creates the schema (cheap: path + parent dir).
  - `Storage.migrate() -> int`: enables WAL once, then applies pending
    migrations, each in a `BEGIN IMMEDIATE` transaction that re-reads
    `user_version` after taking the lock and sets it on success. Returns
    the final version.
  - `Storage.require_current()`: raises `SchemaOutOfDateError` (clear
    message: "run backend/migrate.py") if `user_version` < latest.
  - `_connect()` becomes a context manager: commit/rollback, then **close**;
    sets `busy_timeout` on every connection.
- `backend/migrate.py` (new): `Storage(config.db_path()).migrate()`, prints
  the version. The deploy step; run from anywhere (`python backend/migrate.py`).
- `backend/api.py`: `get_storage()` dependency (reads `config.db_path()` per
  request, so env-based test isolation still works); route takes
  `storage: Storage = Depends(get_storage)`; FastAPI `lifespan` calls
  `require_current()` so the API refuses to start on a stale schema.
- `backend/scheduler.py`: `run_forever` calls `require_current()` before
  the first cycle.
- `backend/main.py`: the `__main__` block (local CLI only) calls `migrate()`
  before `main()`. `main()` itself does NOT migrate — the scheduler calls it
  every cycle and the deploy owns migration.
- `deploy/deploy.sh`: `venv/bin/python backend/migrate.py` between
  `pip install` and `systemctl restart`.
- Existing tests: anywhere a test relied on `Storage(path)` creating tables,
  it now also calls `migrate()`.
- `AGENTS.md`: add the migrate command; note the deploy step.

## Out of scope

`city` column, indexes, retention, discovery table, any API response change.

## TDD sequence (one red/green cycle each)

1. `migrate()` on a fresh DB creates `scrape_runs` + `slots` and sets
   `user_version` to the latest (1). (Replaces `test_storage_initializes_schema`.)
2. `migrate()` is idempotent: second call is a no-op and keeps data.
3. A legacy DB (old tables + rows, `user_version` 0) migrates to v1 with its
   rows intact.
4. A failing migration rolls back fully and leaves `user_version` unchanged
   (inject a bad migration list).
5. Migrations apply in order and only the pending ones (inject a 2-entry
   list on a v1 DB; only entry 2 runs).
6. `migrate()` turns on WAL (`PRAGMA journal_mode` == `wal`).
7. `Storage.__init__` does not create tables.
8. `require_current()` raises `SchemaOutOfDateError` on an unmigrated /
   behind DB; passes when current.
9. `_connect()` closes the connection on exit and commits on success /
   rolls back on error.
10. Every connection has `busy_timeout` set.
11. API: `get_storage` is injectable via `dependency_overrides` (convert
    `make_client` to it); behaviour of existing API tests unchanged.
12. API startup (`with TestClient(app)`) fails on a stale schema and succeeds
    on a migrated one.
13. Scheduler: `run_forever` raises `SchemaOutOfDateError` on a stale DB
    before scraping; existing scheduler tests migrate their tmp DB first.
14. `migrate.py` main entry migrates the configured DB.
15. `deploy.sh` runs `migrate.py` after `pip install` and before
    `systemctl restart` (text-order check).

## Risks

- Switching an existing DB to WAL needs a brief exclusive lock. The deploy
  runs `migrate.py` while the old API/scheduler are still up; if it ever
  reports "database is locked" the deploy fails safely (old services keep
  running) and can simply be re-run.
- `main.main()` no longer creates the schema, so any other caller of
  `Storage` must migrate first (`require_current()` makes that loud).

## Manual checklist (for the user, before committing)

1. `venv\Scripts\python.exe -m pytest` passes.
2. Copy `data\rmt-finder.db` to a temp path, point `RMT_FINDER_DB_PATH` at
   it, run `python backend\migrate.py`; confirm version 1, rows intact,
   `PRAGMA journal_mode` is `wal`.
3. Run `migrate.py` twice: second run is a no-op.
4. Start the API against a brand-new empty DB path without migrating:
   it must refuse to start with the "run migrate.py" message. Then migrate
   and start it: `/api/availability` works.
5. `python main.py` from `backend\` on a fresh DB path still works end to
   end (auto-migrates).
6. Read `deploy/deploy.sh` once more; the migrate line sits before the
   restart.
