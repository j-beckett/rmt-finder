# Availability API

**Type:** AFK

**Done in `74b9ce3`.**

## Parent PRD

`docs/prd/vertical-slice.md`

## What to build

The read-only serving layer. A FastAPI app (run under uvicorn) exposing
`GET /api/availability`, which returns the slots of the latest good run plus
the envelope, per the PRD's "Serving rule" and "API" sections:

- Envelope: served run's `scraped_at`, latest attempt timestamp, clinics
  attempted, and which clinics failed.
- Serving rule: latest run with at least one successful clinic; if the most
  recent attempt had zero successes, fall back to the most recent good run
  (the envelope's two timestamps let the client detect this).
- Cosmetic city filter query param.
- CORS allows the frontend dev server origin.
- The API process never scrapes and reads only through the storage module.

Demoable with curl against a database populated by the scrape CLI.

## Acceptance criteria

- [x] `GET /api/availability` returns the latest good run's slots with the
      full envelope
- [x] When the latest attempt had zero successes, the response serves the
      most recent good run and the envelope's latest-attempt timestamp is
      newer than the served `scraped_at`
- [x] Empty-but-successful run returns an empty slot list with a normal
      envelope (distinguishable from the fallback case)
- [x] City query param accepted; no POST routes, no auth, no pagination
- [x] CORS permits the frontend dev origin
- [x] All data access goes through the storage module
- [x] TestClient tests (written first): normal, empty, envelope contents,
      fallback; `pytest` passes

## Blocked by

- `docs/plans/vertical-slice/01-scrape-to-sqlite.md`

## User stories addressed

- User story 8 (API half)
- User story 20
- User story 21
