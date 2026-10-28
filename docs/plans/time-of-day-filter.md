# Implementation plan — Time-of-day filter

Status: built 2026-10-28, awaiting the user's manual check before commit.

## Goal

End-of-year availability is up (93 Victoria slots over two days on
2026-10-28, only 13 after 5pm). Let people narrow the list to the part of
the day they can actually go, instead of scrolling past everything else.

## Decisions (grilled 2026-10-28)

- **Hide, not group.** Non-matching slots are filtered out; no section
  headers (the parked "group by time of day" idea in `NOTES.md`).
- **Segmented bar under the day pills:** Morning · Afternoon · Evening,
  single-select, nothing selected by default, the day pills' height (the
  44px first cut felt chunky next to them). Tapping the
  active segment clears it; a "Clear time" link shows while one is set.
  Mockup: https://claude.ai/artifact/JLsGiKE4S96MB6tpQW6bwu (board C).
- **Cutoffs, clinic-local time:** Morning < 12:00 ≤ Afternoon < 17:00 ≤
  Evening. Live slots trough at 16:00–18:00, so the 5pm line moves few slots.
- **Range shown in the count line** only while filtered:
  "8 evening openings · 5pm on".
- **Empty state when the time filter empties the list:** "No evening
  openings today" / "There are 12 openings at other times today" / Clear
  time. If the day itself is empty, the existing day empty state wins.
- **Not persisted.** Plain state like the day window: survives a city
  switch, resets on reload, not in the URL.
- **GoatCounter event** `filter/time/<bucket>` on select (not on clear).
  Time of day skews it; read it as "is this used", not preference.
- **Always enabled.** Empty buckets aren't dimmed or disabled.
- Day and time filters are independent; frontend only, no API change.

## Steps

1. `lib/slots.ts`: `timeOfDay(slot)` and `filterSlotsByTime` (tests in
   `slots.test.ts`).
2. `lib/format.ts`: `timeFilterSummary` and `dayPhrase` copy helpers
   (tests in `format.test.ts`).
3. `lib/analytics.ts`: `timeFilterPick` hit (test in `analytics.test.ts`).
4. `components/TimeFilter.tsx` segmented bar; `App.tsx` holds the state;
   `Availability.tsx` wires the count line and empty state; `.time-seg`
   styles in `index.css`.
