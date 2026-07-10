# PRD — Vertical Slice: Scheduled Scrape → SQLite → FastAPI → React Frontend

Builds on the settled decisions in `docs/plans/vertical-slice-decisions.md`
(resolved 2026-07-09 via grill-me). This PRD does not re-open those decisions;
it consolidates them with the remaining details resolved during the PRD
interview (2026-07-09).

## Problem Statement

Someone looking for a massage appointment in Victoria has to check each
clinic's booking site individually. The scraper already solves the collection
problem — it fetches RMT availability from ~23 Jane App clinics — but its
output is a console printout and a timestamped JSON file. There is no way to:

- see current availability without running a script from a terminal,
- have the data refresh itself on a schedule,
- trust that what you're looking at is fresh (or know when it isn't),
- know whether the data is complete (some clinics fail intermittently).

Separately, this project is a portfolio piece for a data engineering role, so
the slice must demonstrate a clean pipeline shape — scheduled ingestion,
immutable storage, a read API, and a presentational frontend — with the
seams (storage, config, scheduling) built so the system can later move off a
single machine without rework.

## Solution

A local-first vertical slice with four parts and SQLite as the only shared
surface:

1. **One-shot scrape CLI** — runs all clinic scrapers once, writes an
   immutable snapshot (a run row plus its observed slots) to SQLite, and
   prints a run summary. The JSON file dump is removed.
2. **Scheduler** — a plain long-running loop that invokes the scrape
   in-process every 15 minutes (configurable). A failing run is logged and
   recorded but never kills the schedule.
3. **Read-only FastAPI service** — `GET /api/availability` returns the slots
   of the latest *good* run (a run where at least one clinic succeeded),
   wrapped in an envelope carrying freshness and completeness metadata.
4. **Minimal React frontend** — one page: a flat, soonest-first list of
   bookable slots (time, clinic, RMT, duration, Book link), a "last updated
   X ago" line, a loud staleness banner when data is old, and honest notices
   when the data is partial or the latest check failed entirely. The page has
   a deliberate warm/wellness visual identity, not library defaults.

The slice is done when scheduler, API, and frontend dev server all run on the
local machine. Hosting is a separate future PRD, but the four
deployment-portability acceptance criteria below guarantee the move is
configuration, not rework.

## Deployment-Portability Acceptance Criteria (non-negotiable)

1. All config/paths via env vars with sensible local defaults
2. One storage module owns all DB access (SQLite now, swappable later)
3. Scrape runs as a one-shot CLI command, schedulable by anything
4. Frontend API base URL is configurable, not hardcoded

## User Stories

1. As a massage-seeking user, I want to see all available RMT slots across
   Victoria clinics on one page, so that I don't have to check each clinic's
   booking site individually.
2. As a massage-seeking user, I want slots sorted soonest-first, so that I
   can find the earliest appointment without scanning the whole list.
3. As a massage-seeking user, I want each slot to show the start time,
   clinic, RMT name, and duration, so that I can judge a slot without
   clicking through.
4. As a massage-seeking user, I want a Book link on each slot that takes me
   to the clinic's booking page, so that I can complete the booking where it
   actually happens.
5. As a massage-seeking user, I want a "last updated X ago" line, so that I
   know how current the availability I'm looking at is.
6. As a massage-seeking user, I want a loud warning when the data is stale
   (older than ~2× the scrape interval), so that I never act on availability
   that is likely wrong.
7. As a massage-seeking user, I want a subtle notice when some clinics
   couldn't be checked in the latest run (e.g. "2 of 23 clinics couldn't be
   checked"), so that I know the list may be incomplete without being
   alarmed.
8. As a massage-seeking user, I want the page to show the most recent run
   that actually has data when the latest check failed entirely — with a
   notice that the last check failed — so that I see the best real data
   available instead of a misleading empty list.
9. As a massage-seeking user, I want a clear, friendly empty state when
   there genuinely are no slots in the next 24 hours, so that I can tell
   "nothing available" apart from "something is broken."
10. As a massage-seeking user, I want slot times shown in the clinic's local
    time, so that the time I see matches the time on the clinic's booking
    page.
11. As a massage-seeking user, I want the page to have a calm, warm,
    wellness-appropriate look, so that using it feels closer to booking a
    massage than reading a server log.
12. As the operator, I want the scrape to run automatically every 15 minutes,
    so that the data stays fresh without me running anything by hand.
13. As the operator, I want one failing run to be logged and recorded without
    stopping the scheduler, so that a transient failure never silently kills
    freshness.
14. As the operator, I want the one-shot scrape CLI to print a run summary
    (run id, clinics scraped, failures, slot count), so that I can verify a
    run at a glance from the terminal.
15. As the operator, I want every run recorded in the database — including
    failed ones, with which clinics failed — so that I can see scrape health
    over time by querying the run history.
16. As the operator, I want the scrape interval, database path, and other
    settings controlled by environment variables with sensible local
    defaults, so that I can change behavior without editing code.
17. As the operator, I want the scrape to be a one-shot CLI command, so that
    I can trigger it manually, from the scheduler loop, or later from cron or
    a cloud scheduler, without changing the scrape itself.
18. As a developer, I want all database access to go through one storage
    module, so that swapping SQLite for another store later touches one
    module only.
19. As a developer, I want snapshots to be append-only (no UPDATEs, no
    deletes), so that the slots table is an immutable fact table I can
    trust for later analysis.
20. As a developer, I want the API process to be strictly read-only (it never
    scrapes), so that serving and ingestion are decoupled and can be
    deployed, scaled, and debugged independently.
21. As a developer, I want the storage module, API endpoints, and scheduler
    failure path covered by pytest written test-first, so that regressions
    are caught by the suite rather than by users.
22. As a developer, I want frontend pure-logic functions (sorting, staleness)
    unit-tested with Vitest, so that display logic is verified without
    brittle component tests.
23. As a developer, I want the frontend's API base URL configurable, so that
    the same frontend code can point at a local or hosted API.
24. As a hiring reviewer of this portfolio project, I want to see a complete
    pipeline — scheduled ingestion into immutable storage, a read API, and a
    presentational client — so that the project demonstrates end-to-end data
    engineering judgment, not just a scraper.

## Implementation Decisions

### Storage

- **Append-only snapshots** in SQLite, two tables:
  - `scrape_runs` — one row per run: id, started/finished timestamps, clinics
    attempted/succeeded, and which clinics failed.
  - `slots` — one row per observed slot per run, foreign-keyed to the run.
    Slot columns mirror the existing scraper result model: clinic name, city,
    platform, RMT name, service type, treatment name, duration in minutes,
    start time (ISO string with timezone offset, as delivered by Jane), and
    booking URL.
- No UPDATEs, no `is_current` flag, no deletes. Immutable fact table.
- **No pruning/retention in this slice.** Data volume is tiny locally;
  retention is parked with a trigger condition (revisit at hosting time or
  if the DB grows meaningfully).
- **One storage module owns all DB access** — schema initialization,
  recording a run, inserting its slots, and reading the latest good run with
  its slots. Nothing else touches the database. SQLite now, swappable later.
- The JSON file dump is removed. SQLite is the only sink.

### Serving rule (what "current availability" means)

- The API serves the **latest good run**, where a good run is simply one with
  at least one successful clinic (`succeeded_count > 0`).
- Partial beats stale: a run where some clinics failed is still served as
  current; the failures are surfaced in the envelope, not hidden.
- If the latest run attempted had zero successes, the API falls back to the
  most recent good run. The envelope always carries both the served run's
  scrape timestamp and the timestamp of the latest attempt, so the client can
  detect and explain the fallback.

### Processes

- **Two long-running processes; SQLite is the only shared surface.**
  - Scheduler: a plain loop that calls the scrape function in-process,
    sleeps, repeats. Runs a scrape immediately on startup, then on the
    interval. A failing run is logged and recorded and the loop continues —
    one bad run must never kill the schedule.
  - FastAPI (uvicorn): read-only serving. Never scrapes.
- Scrape interval: **15 minutes default**, via `SCRAPE_INTERVAL_MINUTES`.
- The scrape itself is a **one-shot CLI command** that runs all clinics,
  writes the snapshot via the storage module, and prints a run summary
  (run id, clinics scraped, failures, slot count). The scheduler calls the
  same function the CLI does; anything else (cron, cloud scheduler) can call
  the CLI.
- The runner's interface changes from "flat list of slots" to "per-clinic
  outcomes plus slots," so the run row can record attempted/succeeded/failed
  per clinic.

### API

- **`GET /api/availability`** — slots of the latest good run, plus an
  envelope: served run's `scraped_at`, latest attempt timestamp, clinics
  attempted, and which clinics failed.
- Read-only API: no POSTs, no auth, no pagination.
- City filter query param allowed but cosmetic (one city today).
- CORS configured to allow the frontend dev server origin.

### Frontend

- **Stack: Vite + React + TypeScript + Tailwind + shadcn/ui**, vendoring
  individual components as needed (likely table, alert, badge). No router,
  no full component library.
- **One page: flat, soonest-first slot list** — time, clinic, RMT, duration,
  Book link — plus a "last updated X ago" line.
- Slot times are displayed in the clinic's local time, derived from the
  timezone offset already present in each slot's start time.
- **Staleness banner (in-slice, not polish):** loud warning when the served
  data's `scraped_at` is older than ~2× the scrape interval.
- **Partial-data notice:** when the served run has failed clinics, a subtle
  line near the last-updated line (e.g. "2 of 23 clinics couldn't be
  checked"). Deliberately quieter than the staleness banner.
- **Failed-latest-check notice:** when the envelope shows the latest attempt
  is newer than the served run (i.e. the latest check failed entirely), the
  page says so and shows when the displayed data is from.
- **Genuine empty state:** when the served run succeeded and simply found no
  slots in the next 24 hours, show a clear, friendly "no availability"
  message — visually distinct from error/failure states.
- **Deliberate visual identity — warm/wellness direction:** warm neutrals,
  generous whitespace, rounded cards, humanist/serif display font.
  Library-default gray is explicitly not acceptable. Iterate via screenshots
  during the build.
- The API base URL is read from frontend configuration (env), never
  hardcoded.

### Configuration

- All config and paths via environment variables with sensible local
  defaults: at minimum the database path, scrape interval, and frontend API
  base URL.

### Testing

- **Backend: pytest, written test-first** (red/green/refactor, per the
  repo's definition of done):
  - Storage module against temporary SQLite databases (schema, run
    recording, slot insertion, latest-good-run reads including the
    zero-success fallback).
  - API endpoints via TestClient: normal case, empty case, envelope
    contents, fallback case.
  - Scheduler failure path: a failing scrape records a failed run and does
    not raise out of the loop.
- **Frontend: Vitest on pure logic functions only** (slot sorting, staleness
  check; later time-of-day grouping if it lands). No component/rendering
  tests; visuals verified by eye against screenshots.

## Out of Scope

Parked deliberately (reasoning and revisit-triggers recorded in the local
notes file):

- **Hosting/deployment** — separate future PRD. The portability criteria
  above exist so that PRD is configuration, not rework.
- **"Refresh now" button** — the API never scrapes in this slice; on-demand
  scraping is real design work (POST endpoint, debouncing, in-progress UI)
  with zero MVP value.
- **Group-by-clinic view and group-by-time-of-day headers** — alternate
  display modes; the flat list ships first.
- **React Router / full component libraries** — single page today; retrofit
  is cheap when a second real route exists.
- **Deduplication** — blocked until filtering is proven clean; duplicates
  signal filtering bugs and must stay visible (per the repo's definition of
  done).
- **Multi-threading the scraper** — sequential runtime (~30–60s) is nowhere
  near the 15-minute interval; parallelism adds rate-limit risk and would
  muddy the existing unexplained flaky-API issue.
- **Retry on the flaky openings API** — the intermittent-empty-response
  cause must be understood before masking it with retries.
- **Data retention/pruning** — no deletes in this slice; revisit at hosting
  time or if local DB size becomes noticeable.

## Further Notes

- The slice is **local-only**: done when scheduler, API, and frontend dev
  server run together on this machine.
- The four deployment-portability acceptance criteria are non-negotiable and
  appear verbatim above; every implementation choice should be checked
  against them.
- After approval, this PRD is broken into independently-gradable
  vertical-slice issues via the prd-to-issues workflow.
