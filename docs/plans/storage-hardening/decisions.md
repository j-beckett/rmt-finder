# Storage hardening — resolved decisions

Outcome of the grill session (2026-10-09). Goal: make storage multi-city ready
and Postgres-ready without moving off SQLite. See also the project memory
`project_postgres_ready.md` for the rules and the audit that motivated this.

## Principles

- Stay on SQLite. One `slots` table with a `city` column, not a table per city.
  Migrate to Postgres only on a real trigger: lock errors WAL can't fix,
  multi-server hosting, or a deliberate history/analytics project.
- All SQL stays inside `Storage`. Timestamps stay ISO 8601 with a tz offset.
  Plain SQL; SQLite-only bits (AUTOINCREMENT, lastrowid, `?`, executescript)
  stay confined to `Storage` and `migrations`.

## Decisions

1. **A run is per city.** `scrape_runs.city`; one row per city per cycle.
   `record_run`, `latest_run`, `latest_good_run` all take a city. A failed
   Vancouver run can never hide a good Victoria run.
2. **Migrations:** hand-rolled, ordered list of numbered SQL migrations using
   `PRAGMA user_version`. No Alembic (two tables, few migrations, no ORM).
   Migration 001 = current schema; an existing prod DB is treated as v1.
3. **Who runs migrations:** a deploy step, `venv/bin/python backend/migrate.py`
   in `deploy/deploy.sh` between `pip install` and `systemctl restart`. A
   failed migration fails the deploy before services restart. API and
   scheduler check `user_version` at startup and refuse to start with a clear
   message if behind. Local `main.py` and test fixtures call `migrate()`
   automatically so normal workflow is unchanged.
4. **Storage lifecycle:** `Storage(path)` has a cheap constructor and an
   explicit `migrate()`. The API gets `Storage` via FastAPI `Depends`
   (tests use `dependency_overrides`). Connections are short-lived and closed
   (`contextlib.closing`); `busy_timeout` per connection; WAL enabled once.
5. **`city` backfill:** existing runs are backfilled to `'victoria'`, column
   `NOT NULL DEFAULT 'victoria'`, default left in place. `record_run` requires
   `city` in Python (test-enforced) so a forgotten city fails loudly instead
   of silently labelling a run Victoria.
6. **Retention:** `RETENTION_DAYS`, default 7, `0` = keep everything. Prune
   old `slots` at the end of a successful scrape; always protect the latest
   good run per city. `scrape_runs` rows kept forever (tiny; a health
   history). Long-term availability history is explicitly not kept; if wanted
   later it needs aggregation before pruning, or Postgres.
7. **Discovery cache** (`clinic_discovery`: subdomain, service_map JSON,
   staff_lookup JSON, config hash, discovered_at). Entry is dropped when:
   TTL expires (`DISCOVERY_TTL_HOURS`, default 24); an openings call for the
   clinic returns non-200; a returned slot has a `staff_member_id` missing
   from the lookup; or the hash of the clinic's service config no longer
   matches (editing `clinics.py` takes effect on the next scrape). An *empty*
   openings list does NOT invalidate (normal for a clinic with no openings,
   and the intermittent-empty TODO in janeapp.py is a separate problem).
8. **API:** `/api/availability?city=` defaults to Victoria, so the live
   frontend works unchanged through the deploy. Unknown city returns 404.
   `clinics_total` becomes per-city. The frontend city dropdown (defaulting to
   Victoria) is a separate HITL design slice, not part of this work.
9. **Scheduler:** one loop, cities scraped sequentially each cycle, one
   `SCRAPE_INTERVAL_MINUTES`. A raising city records a zero-success run for
   that city and the loop continues to the next city.

## Why sequential scraping (and the plan for parallel)

Sequential keeps upstream concurrency at 1 (respectful to Jane's unofficial
endpoint) and keeps SQLite to a single writer. Today a run takes a few
minutes, so it fits the 15-minute interval with one city.

It stops fitting when `cities x run duration` approaches the interval. Plan
if/when that happens, driven by measured run durations, not guesses:
1. Per-city intervals / refresh tiers (busy cities more often, quiet ones
   on demand or skipped overnight), with a single loop waking whenever a
   city is due.
2. Then concurrency across cities (threads or separate scheduler units),
   with a global cap on simultaneous requests to Jane and jitter.
   SQLite is ready for this: WAL + `busy_timeout`, short transactions, and
   `BEGIN IMMEDIATE` for writes if lock contention appears. The adapter is
   already safe to share (one session per clinic scrape).
3. If concurrent writers still contend, that is a Postgres trigger.

## Slices (each independently deployable, in order)

1. **Migration foundation** — runner, `migrate.py`, deploy step, startup
   version check, closed connections, busy_timeout, WAL, `Depends`. No user
   visible change.
2. **Per-city runs** — migration 002 (`scrape_runs.city`, indexes
   `slots(city, start_at)` and `slots(run_id)`), city-aware Storage methods,
   scheduler per-city loop, API default/404, per-city `clinics_total`.
3. **Retention** — `RETENTION_DAYS` pruning.
4. **Discovery cache** — migration 003 `clinic_discovery` + invalidation.

Follow-ups (not in this work): city dropdown (HITL design), per-city refresh
tiers, GoatCounter analytics, `num_days=2` -> `lookahead_days()` cleanup.
