# Scrape-to-SQLite pipeline

**Type:** AFK

## Parent PRD

`docs/prd/vertical-slice.md`

## What to build

The ingestion tracer bullet: a one-shot scrape that lands an immutable
snapshot in SQLite instead of a JSON file. Cuts through runner → storage →
CLI:

- The runner returns per-clinic outcomes (attempted / succeeded / failed
  with which clinics failed) alongside the slots, not just a flat slot list.
- A storage module owns ALL database access: schema initialization
  (`scrape_runs` + `slots` per the PRD's Storage section), recording a run,
  inserting its slots, and reading the latest good run with its slots
  (including the zero-success fallback read — built here, consumed by the
  API slice).
- The CLI entrypoint becomes: run all clinics once, write the snapshot via
  the storage module, print the run summary (run id, clinics scraped,
  failures, slot count). The JSON dump to `data/` is removed.
- Database path comes from an env var with a sensible local default.

Storage tests are written test-first against temporary SQLite databases.

## Acceptance criteria

- [ ] Running the CLI once creates/updates the SQLite DB with one new
      `scrape_runs` row and its `slots` rows (append-only: reruns add rows,
      never modify existing ones)
- [ ] The run row records started/finished timestamps, clinics
      attempted/succeeded, and which clinics failed
- [ ] Slot rows carry clinic name, city, platform, RMT name, service type,
      treatment name, duration, start time (ISO with offset), booking URL,
      and the run FK
- [ ] The CLI prints the run summary; no JSON file is written
- [ ] No code outside the storage module touches the database
- [ ] DB path configurable via env var, defaults sensibly
- [ ] Storage tests (written first) cover schema init, run recording, slot
      insertion, latest-good-run reads incl. zero-success fallback; `pytest`
      passes

## Blocked by

None - can start immediately

## User stories addressed

- User story 14
- User story 15
- User story 16
- User story 17
- User story 18
- User story 19
