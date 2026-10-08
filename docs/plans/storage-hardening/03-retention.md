# Implementation plan — Slice 3: retention

Decisions: `docs/plans/storage-hardening/decisions.md` (item 6).
Builds on slices 1 and 2 (`01-migration-foundation.md`, `02-per-city-runs.md`).
No schema change, no frontend change.

## Goal

Stop `slots` growing forever. Every 15-minute run inserts ~100 slot rows per
city and nothing deletes them. After a successful scrape, delete the slots of
runs that finished more than `RETENTION_DAYS` ago, except each city's latest
good run, which the API falls back to when a city's scrapes keep failing.

## Rules

- `RETENTION_DAYS` env var, default 7; `0` keeps everything.
- Only `slots` rows are deleted. `scrape_runs` rows are kept forever (tiny;
  they are the health history).
- Age is the run's `finished_at`, not the slot's `start_at`.
- Each city's latest good run (highest `id` with `clinics_succeeded > 0`, the
  same rule `latest_good_run` uses) is never pruned, however old. Protection
  is per city.
- Pruning runs at the end of `main.scrape_city`, after `insert_slots`, and
  only when that scrape had at least one successful clinic. A failed or
  zero-success scrape never deletes anything.

## Open details (decided here, flagged for review)

1. **Cutoff comparison.** `finished_at` is ISO 8601 with a UTC offset. Python
   computes `cutoff = now - timedelta(days=retention_days)` as an aware
   datetime and passes its ISO string; SQL compares
   `julianday(finished_at) < julianday(?)`. SQLite's date functions parse the
   `+HH:MM` offset and normalise to UTC, so the comparison is correct even if
   a row was ever written with a non-UTC offset (a plain string comparison
   would only be correct while every writer uses `+00:00`). An unparseable
   `finished_at` makes `julianday()` NULL, so that run is kept (fails safe).
   `julianday` is a SQLite-ism confined to `Storage`; the Postgres port is
   `finished_at::timestamptz < $1`.
   Alternatives considered: plain string comparison (relies on every writer
   using UTC; true today but unenforced); parsing in Python and deleting by an
   id list (portable, but needs chunking around SQLite's bound-variable
   limit).
2. **One DELETE, not batched.** A single
   `DELETE FROM slots WHERE run_id IN (<prunable runs>)` in one short
   transaction. In steady state it removes ~100 rows per city per run. The
   one large delete is the first prune in production (every slot since
   launch). Under WAL the API keeps reading during it, and the scheduler is
   the only writer, so the only cost is a few seconds of write lock and a
   temporarily larger WAL file. Measured on synthetic data (85 days x 96
   runs x 100 slots = 816k rows): the first prune deleted 749k rows in 2.2s;
   a steady-state prune takes ~16ms. Batching is not needed.

## Files to touch

- `backend/config.py`: `retention_days()` with a docstring, matching the
  other settings.
- `backend/storage.py`: `prune_slots(retention_days, now=None) -> int`
  (rows deleted). `now` is injectable for tests; defaults to UTC now.
  `retention_days <= 0` returns 0 without touching the database.
- `backend/main.py`: `scrape_city` calls `prune_slots(config.retention_days())`
  after `insert_slots` when `result.succeeded` is non-empty, and prints
  `Pruned N slot(s) older than D day(s)` when N > 0.
- Tests: `test_config.py`, `test_storage.py`, `test_main.py`.

## Out of scope

Pruning `scrape_runs`; aggregating history before pruning; `VACUUM` (SQLite
reuses freed pages, so the file stops growing rather than shrinking; a manual
`VACUUM` is optional, once, after the first prune).

## TDD sequence (one red/green cycle each)

1. `config.retention_days()` defaults to 7.
2. `config.retention_days()` reads `RETENTION_DAYS` (incl. `0`).
3. `prune_slots` deletes slots of a run older than the cutoff and keeps a
   newer run's slots; returns the number deleted.
4. `prune_slots` never deletes `scrape_runs` rows.
5. `prune_slots` keeps a city's latest good run even when it is older than
   the cutoff.
6. Protection is per city: city A's latest good run does not protect city
   B's old good run (that is not B's latest), and B's latest good is kept.
7. A newer zero-success run does not take protection away from the latest
   good run (protection follows `clinics_succeeded > 0`, not "latest run").
8. Offset-aware cutoff: a `finished_at` written with a non-UTC offset is
   compared by instant, not by string.
9. `retention_days=0` deletes nothing.
10. `scrape_city` prunes after a successful scrape and prints the line.
11. `scrape_city` with zero successful clinics does not prune.
12. `scrape_city` prints nothing about pruning when nothing was deleted.

## Risks

- **First production prune is big.** ~3 months of 15-minute runs is on the
  order of 800k slot rows: ~2s on synthetic data. The manual checklist also
  times it on a copy of the real database.
- **Prune failure inside `scrape_city`.** If `prune_slots` raised, the
  scheduler's `run_once` would log it and record an extra zero-success run
  even though the scrape itself was good. Not guarded in this slice (a
  failing DELETE should be loud); flagged in case a try/except is preferred.
- **Clock.** The cutoff uses the server clock. A clock jump forward could
  prune early, but the latest good run per city is always protected, so the
  API never loses its fallback.

## Revision: prune per city (before first commit)

A scale check showed the global prune's cost growing with `scrape_runs`,
which is kept forever: one prune took 57ms at 35k runs, 0.5s at 350k and
1.6s at 1.05M (10 cities x 3 years). Every city's scrape also pruned every
city, so that work happened N times per cycle. Changed before shipping:

- `prune_slots(city, retention_days, now=None)`: only that city's slots,
  called by `scrape_city` with its own city.
- Protection is that city's newest good run (`ORDER BY id DESC LIMIT 1`
  on the `(city, id)` index), the same lookup `latest_good_run` does.
- Candidate runs start at `MIN(run_id)` in `slots` (one lookup on the
  `slots(run_id)` index): older runs have nothing left to delete, so the
  cost is bounded by the retention window, not the history. A city whose
  scrapes have failed for a long time holds that bound back via its
  protected run; that only widens the scan, never changes the result.
- Measured in steady state (10 cities, 7 days of slots, one city's prune):
  global version 57ms / 0.5s / 1.6s at 35k / 350k / 1.05M runs;
  city-scoped 6ms / 55ms / 184ms; city-scoped + `MIN(run_id)` bound
  1.6ms / 1.7ms / 1.7ms. Every step of the query plan is an index search.
- Known consequence: a city dropped from the roster is no longer scraped,
  so its last slots are never pruned. Rare and deliberate; clean up by hand.

TDD additions:
13. `prune_slots` takes a city; `scrape_city` passes its own (signature
    change: existing tests go red with TypeError, then green).
14. Pruning one city leaves another city's old slots alone.
15. Query narrowed to runs that still have slots: a performance change with
    no behaviour change, so it cannot be seen red in a test; proven with the
    scale benchmark instead.

## Manual checklist (for the user, before committing)

1. `venv\Scripts\python.exe -m pytest` passes (96 tests).
2. Take a consistent copy of the production database (the backup API is safe
   while the scheduler is writing; never run the prune against the live file):

   ```bash
   ssh rmt@<droplet> 'cd ~/rmt-finder && venv/bin/python -c "import sqlite3; sqlite3.connect(\"data/rmt-finder.db\").backup(sqlite3.connect(\"/tmp/rmt-copy.db\"))"'
   scp rmt@<droplet>:/tmp/rmt-copy.db data/rmt-copy.db
   ```

3. Locally, prune the copy and compare before/after:

   ```bash
   venv/Scripts/python.exe - data/rmt-copy.db <<'EOF'
   import sqlite3, sys, time
   sys.path.insert(0, "backend")
   from storage import Storage

   db = sys.argv[1]
   q = lambda sql: sqlite3.connect(db).execute(sql).fetchall()
   GOOD = ("SELECT r.city, r.id, r.finished_at, COUNT(s.id) FROM scrape_runs r"
           " LEFT JOIN slots s ON s.run_id = r.id WHERE r.id IN (SELECT MAX(id)"
           " FROM scrape_runs WHERE clinics_succeeded > 0 GROUP BY city)"
           " GROUP BY r.id")
   OLD = ("SELECT COUNT(*) FROM slots WHERE run_id IN (SELECT id FROM scrape_runs"
          " WHERE julianday(finished_at) < julianday('now', '-7 days'))")
   before = (q("SELECT COUNT(*), MAX(id) FROM scrape_runs"), q("SELECT COUNT(*) FROM slots"), q(OLD), q(GOOD))
   print("before: runs", before[0], "slots", before[1], "old slots", before[2], "latest good", before[3])
   t = time.perf_counter(); n = Storage(db).prune_slots("victoria", 7); t = time.perf_counter() - t
   print(f"pruned {n} rows in {t:.2f}s")
   after = (q("SELECT COUNT(*), MAX(id) FROM scrape_runs"), q("SELECT COUNT(*) FROM slots"), q(OLD), q(GOOD))
   print("after:  runs", after[0], "slots", after[1], "old slots", after[2], "latest good", after[3])
   EOF
   ```

   Expect: `runs` identical before and after (scrape_runs untouched); `old
   slots` drops to 0 (or only the latest good run's slots, if that run is
   itself older than 7 days); `latest good` identical before and after, same
   run id and slot count per city; `pruned` equals the slot-count difference;
   the time is a few seconds at most.
4. `RETENTION_DAYS=0` keeps everything: take a fresh copy (step 2), run
   `RETENTION_DAYS=0 RMT_FINDER_DB_PATH=../data/rmt-copy.db python main.py` from
   `backend\` and check no "Pruned" line is printed and the slot count only
   grew. Then without `RETENTION_DAYS` on the same copy: one
   `Pruned N slot(s) older than 7 day(s)` line appears.
5. Delete `data/rmt-copy.db` when done (it is not in git; check
   `git status`).
6. Optional, once after the first production prune: `VACUUM` to shrink the
   file. Not required; SQLite reuses the freed pages.
