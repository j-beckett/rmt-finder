# Implementation plan — Slice 01: clinic slugs

Issue: `docs/plans/goatcounter-analytics/01-clinic-slugs.md`
Status: built 2026-10-09, awaiting the user's manual check before commit.

## Decisions

- Slug values are the owner-approved list (2026-10-09), written as literals.
- `jane_rmt(..., *, slug=...)` is a required keyword-only argument, so it
  can't be swapped with `subdomain` (both strings) by position.
- `AvailabilityResult.clinic_slug: str | None` is required (no default) so an
  adapter can't forget it; `None` only for rows scraped before migration 3.
- Frontend `Slot.clinic_slug` is `string | null`: until the first post-deploy
  scrape, the API may serve a pre-migration run whose rows have no slug.
- The API dedupe key stays (clinic name, therapist, start, duration).

## Steps (test-first, one at a time)

1. `tests/test_clinic_slugs.py`: every clinic has a slug; format
   `^[a-z0-9]+(-[a-z0-9]+)*$`; unique across cities; Equilibrium entries
   start with `equilibrium-`. → add `slug` to `ClinicConfig`, `jane_rmt`, and
   the approved values in `CLINICS`.
2. Adapter: a fetched slot carries `clinic_slug` from its clinic config.
   → add the field to `AvailabilityResult`; set it in `janeapp._fetch_openings`.
3. Migration 3: upgrading a version-2 DB keeps old rows, which read back with
   `clinic_slug = None`. → append `ALTER TABLE slots ADD COLUMN clinic_slug TEXT`.
4. Storage round trip: a slot written with a slug reads back with it.
   → `insert_slots` / `latest_good_run` write and read the column.
5. API: `/api/availability` slots include `clinic_slug` (no code expected;
   `_slot_dict` uses `asdict`).
6. Frontend: `Slot` type, mock envelopes and the vitest helper gain
   `clinic_slug`; `npm test` and `npm run build` pass.
