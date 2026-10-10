# Frontend tracking + README

**Type:** AFK

## Parent PRD

`docs/prd/goatcounter-analytics.md`

## What to build

The frontend sends clean city page views and per-clinic Book clicks to
GoatCounter. The owner can opt their browsers out, and nothing breaks if the
script is missing. The README describes the setup. See PRD "Implementation
Decisions → Event contract", "Frontend modules", "Owner opt-out" and "Docs".

- **Analytics core (pure functions, vitest, test-first):**
  - page-view decision from app state. Implements every row of the PRD's
    event contract table: `/<servedCity>`, `/unknown-city` with the raw value
    in the title, and nothing on API/network errors.
  - Book-click event from a slot: `book/<clinic_slug>`, with the clinic
    display name as title.
  - trackable-click test: primary click yes, middle-button `auxclick` yes,
    anything else no.
  - opt-out handling: `?notrack` sets a persistent local-storage flag,
    `?notrack=off` clears it. Storage errors are treated as not opted out.
- **Tracker wrapper:** calls GoatCounter's `count()`. It does nothing when
  opted out, when the script is absent (blocked, failed, or not yet live), or
  outside production builds. It never throws. Tests use a fake `count()`.
- **Script loading:** GoatCounter's script from `stats.studiobeckett.ca`, in
  production builds only, with automatic on-load counting disabled.
- **Wiring:**
  - send a page view when the availability state settles (first load, city
    switch, Back/Forward)
  - attach `click` and `auxclick` handlers to slot cards
  - slot-card link behaviour is unchanged (new tab, `noopener noreferrer`,
    no delay)
- **README:** in "How it works", add a GoatCounter node to the diagram
  (frontend → self-hosted GoatCounter: city views, Book clicks) and a short
  paragraph: self-hosted and cookieless, what is tracked and why, owner
  traffic opted out, and empty-results tracking deliberately dropped. Do not
  link the dashboard.

Opt-out must ship in the same deploy as (or before) the first hits, never
after.

## Acceptance criteria

- [x] vitest covers every event-contract row, including: default city with no
      `?city=`, city switch, Back/Forward, unknown city (raw value in title,
      not path), and API error (no hit)
- [x] vitest covers trackable clicks: left yes, middle yes, right no
- [x] vitest covers opt-out: set, persist, clear with `=off`, throwing storage
- [x] vitest covers the wrapper: no-op when opted out, when `goatcounter` is
      absent, and outside production; never throws
- [x] Tracking params (`fbclid`, `utm_*`) never appear in a page-view path
- [ ] Dev server makes no request to `stats.studiobeckett.ca`
- [x] Production build includes the script with on-load counting disabled
- [ ] Page and booking links work normally with the script blocked
- [x] No component-level tests needed: the wiring stays thin, and the logic
      lives in the tested functions
- [ ] README diagram renders and the paragraph matches what is tracked
- [x] `npm test`, `npm run build`, `npm run lint` and `pytest` pass

## Blocked by

- `docs/plans/goatcounter-analytics/01-clinic-slugs.md`

## User stories addressed

- User story 1
- User story 2
- User story 3
- User story 4
- User story 5
- User story 6
- User story 7
- User story 8
- User story 9
- User story 12
- User story 13
- User story 14
- User story 15
- User story 16
- User story 17
- User story 18
- User story 19
- User story 20
- User story 21
- User story 22
- User story 38
- User story 39
- User story 40
- User story 44
- User story 46
- User story 47
