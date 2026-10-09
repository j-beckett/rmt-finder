# Implementation plan — Quiet hours (DRAFT)

Status: final (questions settled 2026-10-08). Ready to build test-first.
Follows storage hardening (slice 4, the discovery cache, was shelved in
favour of this; see `docs/plans/storage-hardening/decisions.md` item 7).

## Goal

Don't scrape overnight. Openings rarely change between 11 pm and 6 am and
nobody books then, but the scheduler scrapes every 15 minutes around the
clock. Skipping 11 pm-6 am skips 28 of 96 runs a day: ~29% of all requests
to Jane (homepages, location pages and openings calls), against ~4% for the
shelved discovery cache.

## Rules

- Two settings in `backend/config.py`, same style as the others, with a
  docstring:
  - `QUIET_HOURS_START` and `QUIET_HOURS_END`, e.g. `23:00` and `06:00`.
  - **Both unset (or empty) = off**: the scheduler scrapes 24/7 as before.
    Both set = on. Only one set, or a malformed value, = the scheduler and
    API refuse to start with a clear message (a typo must not silently
    leave it scraping all night).
  - 24-hour `HH:MM`, read as **each city's local time**. Start is inclusive,
    end is exclusive: a scrape due at 06:00 runs.
  - The window may cross midnight (start later than end) and usually will.
  - Start equal to end is rejected as malformed (it is ambiguous: all
    night or never).
  - A window longer than 12 hours (e.g. `22:00` to `20:20`, 22h20m) is
    valid but almost certainly a typo: the scheduler and API start, and log
    a warning naming the length and both settings.
  - Production only goes quiet once both are set on the droplet, for
    **both** `rmt-scheduler` (to skip) and `rmt-api` (to report the window
    to the frontend).
- Checked per city, just before that city's scrape, in the city's IANA zone
  (`config.timezone_for_city`). Never a fixed UTC offset.
- Only the scheduler skips. `python main.py` always scrapes (a local run is
  deliberate).
- A skipped city records nothing and does not prune: `scrape_runs` stays a
  history of real attempts, and the API reports quiet hours itself.
- The loop keeps its 15-minute tick through the night and simply skips, so
  the first scrape after the window is at the first tick at or after 06:00
  (up to 15 minutes late). No "sleep until morning" arithmetic, which is
  where DST bugs live.

## Time zones and BC's permanent UTC-7 (1 November 2026)

BC stays on UTC-7 permanently; the 1 November 2026 fall-back does not
happen. The IANA time zone database models this from release **2026b**:
`America/Vancouver` stays at UTC-7 after 2026-11-01 02:00. Any system with
older data will move Vancouver back to UTC-8 that night, shifting the quiet
window an hour (real 10 pm-5 am).

- Quiet hours is the first backend code that converts time zones (today the
  backend only passes Jane's offsets through and reports the zone name).
- Python's `zoneinfo` reads the operating system's tz data first and falls
  back to the `tzdata` PyPI package. Windows has no system data, so locally
  `ZoneInfo("America/Vancouver")` currently fails: `tzdata` is not
  installed. The droplet uses Ubuntu's `tzdata` package, which must be
  2026b or later.
- Decided: pin `tzdata` (>= 2026.2, i.e. 2026b) in `requirements.txt` and make
  Python use only it (`zoneinfo.reset_tzpath(to=[])` once, in `config`), so
  dev, CI and the droplet all use the version in git; upgrading tz data is a
  normal dependency bump. A canary test asserts `America/Vancouver` is UTC-7
  on 2026-12-01, so stale data fails CI instead of failing silently. Worth
  shipping before 2026-11-01 even if the rest of quiet hours is later.
- Frontend: slot times are shown from Jane's own offsets, so they are
  unaffected. `todayInZone` uses the viewer's browser tz data; a browser
  with stale data would get "today" wrong for about an hour after midnight.
  Minor, outside our control, noted only.

## Overnight messaging (decided 2026-10-08)

Today the frontend shows "This availability is out of date ... we haven't
been able to refresh for a while" once served data is older than 2x the
scrape interval (30 minutes). Without changes, that banner would appear
every night with a wrong message: nothing failed.

**Design: meta line only (option A).** No banner, no notice box: quiet hours
is not a problem, so it gets the quietest treatment the page has. The slot
list stays visible (people browsing at night are planning tomorrow, and the
booking links work). Under "Last updated ...":

> We pause checks overnight and start again at 6 am.

The time comes from the settings (city-local, formatted like the rest of the
page), never hard-coded.

When it shows (these matter more than the wording):

1. **Only if the data is from around the start of quiet hours.** If the last
   good scrape is older than the quiet start minus 2x the interval (a check
   failed before the night began), the real "out of date" banner shows as
   today. Quiet hours never hides a genuine failure.
2. **Grace after the window ends.** The first morning scrape lands at the
   first tick at or after 06:00 and takes a few minutes. The quiet treatment
   (no stale banner) lasts until that scrape completes, up to 2x the
   interval after the window ends, so the banner doesn't flash at 6 am.

So the API reports the current or most recent window, not just a flag:
e.g. `quiet_hours: {start: <iso>, end: <iso>}` for the window that
contains now or ended most recently (null when quiet hours are off). The
frontend's freshness rules use it; they stay pure functions with tests.

## Decisions (settled 2026-10-08)

1. On when both times are set, off when neither is; one alone or a bad
   value fails startup.
2. Skipped runs record nothing.
3. Pinned `tzdata` package is the only tz source, everywhere.
4. Overnight message: option A (meta line only), see above.

## TDD sequence

1. Canary: `America/Vancouver` is UTC-7 on 2026-12-01, using the pinned
   `tzdata` package only (tz path reset).
2. `config.quiet_hours()`: both unset = None (off); both set = the window;
   one alone, malformed, or start == end raise a clear error.
3. `is_quiet(city, now)`: off = never quiet; inside, outside, both
   boundaries, a window crossing midnight.
4. `is_quiet` uses the city's zone: the same UTC instant is quiet in one
   zone and not another.
5. `is_quiet` across 2026-11-01: 06:00 local on 2 November is 13:00 UTC
   (UTC-7, no fall-back), not 14:00.
6. `scheduler.run_once` skips a quiet city: no scrape, no run recorded.
7. `run_cycle` scrapes non-quiet cities and skips quiet ones.
8. Scheduler startup fails clearly on malformed settings.
8b. A window over 12 hours logs a warning at startup (and still starts).
9. API: envelope reports the current or most recent quiet window
   (`quiet_hours: {start, end}`, null when off).
10. Frontend freshness: inside the window (and data from around its start)
    → quiet, not stale; data older than the window start → stale as today;
    grace until 2x interval after the window ends.
11. Frontend: the meta line shows "We pause checks overnight and start
    again at <end time>." while quiet; no banner.

## As built (notes and deviations)

- `config.quiet_hours()` returns `QuietHours(start, end)` or None; strict
  `HH:MM` parsing (rejects `6`, `25:00`, `+1:00`, ` 1:00`).
- `backend/quiet_hours.py`: `is_quiet`, `last_window` (the window the API
  sends), `long_window_warning` (> 12h, logged at startup by both services).
- Scheduler: `run_once`/`run_cycle`/`run_forever` take `quiet` and an
  injectable `clock`; settings read once at boot.
- API: `quiet_hours: {start, end}` (city-local ISO) or null; a `get_clock`
  dependency for tests; refuses to start on bad settings.
- Frontend: `isQuietPause` and `quietNote` in `lib/freshness.ts`; the note
  replaces the stale banner. The resume time uses the site's existing
  `formatSlotTime`, so it reads "6:00 AM" (not "6 am"), matching slot times,
  and comes from the window's own offset, immune to stale browser tz data.
- The note also shows during the 30-minute morning grace, while the first
  check runs ("start again at 6:00 AM" at 06:10 is still true enough).
- Dev mocks: `?mock=quiet` and `?mock=quiet-failed`. Their times are relative
  to now, so the resume time shown is "now + 3h", not 6:00 AM.
- Not changed: the intro copy "rechecked every 15 minutes" (true by day).

## Manual checklist

1. Tests: `venv\Scripts\python.exe -m pytest` (149) and, in `frontend\`,
   `npx vitest run` (43); `npm run build` passes.
2. Look at the states in the dev server (`npm run dev` in `frontend\`):
   `?mock=quiet` shows the note and no banner; `?mock=quiet-failed` shows the
   "out of date" banner; `?mock=fresh` and `?mock=stale` are unchanged.
3. Scheduler, locally, with a window around the current time (e.g. if it is
   14:20, use 14:00 to 15:00):
   `QUIET_HOURS_START=14:00 QUIET_HOURS_END=15:00 RMT_FINDER_DB_PATH=data/qh-test.db venv/Scripts/python.exe backend/migrate.py`
   then the same env with `venv/Scripts/python.exe backend/scheduler.py`:
   the log says "Quiet hours: skipping victoria" and nothing is scraped.
   Ctrl+C. Delete `data/qh-test.db*`.
4. Bad settings fail at startup: `QUIET_HOURS_START=23:00` alone (and
   `QUIET_HOURS_START=11pm QUIET_HOURS_END=06:00`) make `scheduler.py` exit
   with a message naming the setting. `22:00`/`20:20` starts with a warning
   mentioning 22h20m.
5. After deploying: set both variables for `rmt-scheduler` and `rmt-api` on
   the droplet (where the services get their environment: see
   `systemctl cat rmt-scheduler rmt-api`), restart both, and check
   `curl -s localhost:8000/api/availability | grep -o '"quiet_hours":[^}]*}'`.
   Until they are set, nothing changes (quiet hours off).
6. First night: the scheduler log shows skips from 23:00; the site shows the
   note, no banner; scraping resumes at the first tick after 06:00.
