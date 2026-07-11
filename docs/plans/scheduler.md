# Implementation plan — Scheduler loop

Issue: `docs/plans/vertical-slice/03-scheduler.md`
PRD: `docs/prd/vertical-slice.md`

## Files to touch

- `backend/scheduler.py` (new) — the second long-running process:
  - `run_once(scrape)` — one cycle: call the scrape function (default
    `main.main`, the same function the CLI runs). If it raises, log the
    exception and record a failed run via `Storage` (0 attempted,
    0 succeeded, no failed-clinic names — the raise happened before
    per-clinic outcomes existed). Never propagates.
  - `run_forever(scrape, sleep)` — scrape immediately on startup, then
    `sleep(interval * 60)`, repeat. `sleep` is injectable so tests can
    break the loop without waiting.
  - `__main__` block: `logging.basicConfig` + `run_forever()`.
  - SQLite is the only shared surface — the scheduler never imports or
    talks to the API.
- `backend/config.py` — add `scrape_interval_minutes()`, env var
  `SCRAPE_INTERVAL_MINUTES`, default 15.

## Run command

`venv\Scripts\python.exe backend\scheduler.py`

## TDD sequence (one red/green cycle each)

1. Failure path (written first, per the issue's acceptance criteria):
   a scrape that raises is logged, recorded as a failed run
   (`clinics_succeeded = 0` so the API's serving rule skips it), and
   does not propagate out of `run_once`.
2. Success path: `run_once` calls the scrape exactly once and records
   nothing itself — the scrape function already records its own run.
3. `config.scrape_interval_minutes()` defaults to 15.
4. `config.scrape_interval_minutes()` honors `SCRAPE_INTERVAL_MINUTES`.
5. `run_forever` scrapes immediately, then sleeps the configured
   interval in seconds between scrapes.
6. `run_forever` keeps cycling when a scrape raises (failure recorded,
   next cycle still runs).
