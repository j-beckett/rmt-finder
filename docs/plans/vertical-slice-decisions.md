# Vertical Slice — Decision Record

Resolved 2026-07-09 via a grill-me session. These decisions are **settled**;
the PRD should build on them, not re-open them. Deliberately parked ideas
live in `NOTES.md` (gitignored, repo root).

## Scope & deployment

1. **Local-only.** The slice is done when it runs on this machine
   (scheduler + API + frontend dev server). Hosting is a separate future PRD.
2. **Deployment-portability acceptance criteria (non-negotiable, verbatim):**
   1. All config/paths via env vars with sensible local defaults
   2. One storage module owns all DB access (SQLite now, swappable later)
   3. Scrape runs as a one-shot CLI command, schedulable by anything
   4. Frontend API base URL is configurable, not hardcoded

## Storage

3. **Append-only snapshots.** Two tables:
   - `scrape_runs` — one row per run: id, started/finished timestamps,
     clinics attempted/succeeded, which clinics failed.
   - `slots` — one row per observed slot per run, FK to `run_id`.
   No UPDATEs, no `is_current` flag. Immutable fact table.
4. **"Current availability" = slots of the latest run**, even if some clinics
   failed in that run (partial beats stale). Failures are recorded on the run
   row so the API can surface incompleteness.
5. **The JSON file dump (`data/*.json`) is removed.** SQLite is the only sink.
   The CLI prints a run summary (run id, clinics scraped, failures, slot count).

## Processes

6. **Two long-running processes, SQLite the only shared surface:**
   - `scheduler.py` — plain loop, calls the scrape function in-process,
     sleeps, repeats. A failing run is logged + recorded and the loop
     continues; one bad run must never kill the schedule.
   - FastAPI (uvicorn) — read-only serving. Never scrapes.
7. **Scrape interval: 15 minutes default**, via `SCRAPE_INTERVAL_MINUTES`.

## API

8. **`GET /api/availability`** — slots from the latest run plus an envelope:
   `scraped_at`, clinics attempted/failed. Read-only API: no POSTs, no auth,
   no pagination. City filter param allowed but cosmetic (one city today).

## Frontend

9. **Stack: Vite + React + TypeScript + Tailwind + shadcn/ui**, pulling
   individual vendored components as needed (likely table, alert, badge).
   No router (add when a second real route exists). No full component library.
10. **One page: flat, soonest-first slot list** (time, clinic, RMT, duration,
    Book link) + "last updated X ago" line.
11. **Staleness banner is in-slice, not polish:** loud warning when
    `scraped_at` is older than ~2× the scrape interval. A 24h-lookahead app
    serving old data is actively wrong, not just stale.
12. **Deliberate visual identity — warm/wellness direction** (warm neutrals,
    generous whitespace, rounded cards, humanist/serif display font).
    Library-default gray is explicitly not acceptable. Iterate via
    screenshots during the build.

## Testing

13. **Backend: pytest, test-first** (per AGENTS.md DoD) — storage module
    (temp SQLite), API endpoints (TestClient: normal / empty / envelope),
    scheduler failure path ("failing scrape records a failed run, doesn't
    raise").
14. **Frontend: Vitest on pure logic functions only** (`sortSlots`,
    `isStale`, later `groupByTimeOfDay`). No component/rendering tests.
    Visuals verified by eye.

## Explicitly out of scope (parked in NOTES.md)

- Hosting/deployment (future PRD)
- "Refresh now" button
- Group-by-clinic view; group-by-time-of-day headers
- React Router; full component libraries
- Dedup (blocked until filtering proven clean — see AGENTS.md DoD)
- Multi-threading the scraper
- Retry on the flaky openings API (investigate cause first)
