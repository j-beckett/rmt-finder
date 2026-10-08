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

## Manual checklist

To be written once the plan is final.
