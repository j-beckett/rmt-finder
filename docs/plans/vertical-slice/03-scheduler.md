# Scheduler loop

**Type:** AFK

**Done in `528a8fc`** (default interval restored to 15 in a follow-up fix).

## Parent PRD

`docs/prd/vertical-slice.md`

## What to build

The second long-running process: a plain loop that calls the same scrape
function the CLI uses, in-process — scrape immediately on startup, then
sleep for the configured interval, repeat. Per the PRD's "Processes"
section:

- Interval from `SCRAPE_INTERVAL_MINUTES`, default 15.
- A failing run is logged and recorded via the storage module, and the loop
  continues — one bad run must never kill the schedule.
- SQLite remains the only shared surface; the scheduler never talks to the
  API.

Demoable by running it and watching consecutive run rows land in SQLite.

## Acceptance criteria

- [x] Starting the scheduler triggers a scrape immediately, then again after
      each interval
- [x] `SCRAPE_INTERVAL_MINUTES` env var respected, defaults to 15
- [x] A scrape that raises is logged, recorded as a failed run, and the loop
      continues to the next cycle
- [x] Scheduler failure-path test (written first): a failing scrape records
      a failed run and does not propagate out of the loop; `pytest` passes

## Blocked by

- `docs/plans/vertical-slice/01-scrape-to-sqlite.md`

## User stories addressed

- User story 12
- User story 13
- User story 16
- User story 21
