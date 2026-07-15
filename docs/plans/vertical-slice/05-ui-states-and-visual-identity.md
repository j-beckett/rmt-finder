# UI states & visual identity

**Type:** HITL

## Parent PRD

`docs/prd/vertical-slice.md`

## What to build

The honesty layer and the design pass, iterated together since both are
screenshot-driven. Per the PRD's "Frontend" section:

**Freshness & completeness states** (each visually distinct):

- **Staleness banner** — loud warning when the served data's `scraped_at`
  is older than ~2× the scrape interval.
- **Partial-data notice** — subtle line near the last-updated line when the
  served run has failed clinics (e.g. "2 of 23 clinics couldn't be
  checked"); deliberately quieter than the staleness banner.
- **Failed-latest-check notice** — when the envelope's latest attempt is
  newer than the served run, say the last check failed and show when the
  displayed data is from.
- **Genuine empty state** — friendly "no availability in the next few days"
  message, visually distinct from every error/failure state.

**Visual identity** — warm/wellness direction: warm neutrals, generous
whitespace, rounded cards, humanist/serif display font. Library-default
gray is explicitly not acceptable. Applied across the slot list AND all the
states above.

`isStale` is a pure function with Vitest coverage. State visuals are
verified by eye (drive them by pointing the frontend at DBs crafted to
exhibit each condition, or by stubbing the API response during review).

**HITL:** design is iterated via screenshots with the human until the look
is approved; each UI state is reviewed by eye.

## Acceptance criteria

- [ ] Staleness banner appears when served data is older than ~2× the
      scrape interval and is unmissable
- [ ] Partial-data notice appears when the served run has failed clinics,
      quieter than the staleness banner
- [ ] Failed-latest-check notice appears when latest attempt > served
      `scraped_at`, showing when the displayed data is from
- [ ] Genuine empty state is friendly and distinct from failure states
- [ ] `isStale` is a pure function with Vitest coverage; Vitest passes
- [ ] Page (all states) reflects the warm/wellness identity — no
      library-default gray
- [ ] Human has iterated on screenshots and approved the final look

## Blocked by

- `docs/plans/vertical-slice/04-frontend-slot-list.md`

## User stories addressed

- User story 6
- User story 7
- User story 8 (UI half)
- User story 9
- User story 11
- User story 22
