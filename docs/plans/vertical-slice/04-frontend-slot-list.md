# Frontend slot list

**Type:** HITL

## Parent PRD

`docs/prd/vertical-slice.md`

## What to build

The first end-to-end user-visible path: a Vite + React + TypeScript +
Tailwind + shadcn/ui app with one page that fetches from
`GET /api/availability` and renders the flat, soonest-first slot list —
time, clinic, RMT, duration, Book link — plus the "last updated X ago"
line. Per the PRD's "Frontend" section:

- Slot times displayed in the clinic's local time (from the offset already
  in each slot's start time).
- API base URL read from frontend env config, never hardcoded.
- shadcn components vendored individually as needed; no router.
- Sorting lives in a pure function (`sortSlots`) unit-tested with Vitest.

This slice is functional-first: correct data, correct order, working Book
links. The deliberate visual identity and the freshness/completeness states
land in the next slice — but don't fight them: structure the page so those
can slot in.

**HITL:** the human eyeballs the first working page in the browser (against
the live API) before the states/design slice builds on it.

## Acceptance criteria

- [ ] Page loads against the running API and lists real slots
      soonest-first with time, clinic, RMT, duration, and a working Book
      link per slot
- [ ] Times render in clinic-local time matching what the clinic's booking
      page shows
- [ ] "Last updated X ago" line derived from the envelope's served
      `scraped_at`
- [ ] API base URL comes from env config; changing it requires no code edit
- [ ] `sortSlots` is a pure function with Vitest coverage; Vitest passes
- [ ] No component/rendering tests (per PRD testing decisions)
- [ ] Human has reviewed the working page in the browser and signed off

## Blocked by

- `docs/plans/vertical-slice/02-availability-api.md`

## User stories addressed

- User story 1
- User story 2
- User story 3
- User story 4
- User story 5
- User story 10
- User story 22
- User story 23
