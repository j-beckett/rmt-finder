# Clinic slugs end to end

**Type:** HITL

## Parent PRD

`docs/prd/goatcounter-analytics.md`

## What to build

Give every clinic location a stable identity that is separate from its display
name, and carry it all the way to the frontend. After this slice, every slot
the API serves includes a `clinic_slug`, and renaming a clinic in config no
longer changes its key. See PRD "Implementation Decisions → Clinic identity"
and "Slug through the pipeline".

- Add a required `slug` to the clinic config. Values are fixed literals: one
  per location, unique across all cities, and locations of the same business
  share a prefix (e.g. `equilibrium-fisgard`).
- **HITL step:** generate a draft slug list from the current clinic names
  (a throwaway script, not committed). Present it to the owner for review and
  shortening **before** writing the values into config. Once a slug is in use,
  changing it splits that clinic's analytics history.
- Adapters set `clinic_slug` on each slot from the clinic config, next to
  `clinic_name`.
- Add a new migration (append to `MIGRATIONS`, never edit a shipped one) for a
  nullable `clinic_slug` column on `slots`. Storage writes and reads it.
- The API response includes `clinic_slug` on each slot. Serialization already
  emits every `Slot` field, so confirm this with a test rather than new code.
- Add `clinic_slug` to the frontend `Slot` type and the mock envelopes.

Built test-first with pytest (red/green/refactor).

## Acceptance criteria

- [ ] Owner has reviewed and approved the slug list before it is committed
- [ ] Every clinic config entry has a slug; a test fails if any is missing
- [ ] A test enforces the format (lowercase letters, digits, hyphens only)
- [ ] A test enforces uniqueness across all cities
- [ ] Multi-location Equilibrium entries share the `equilibrium-` prefix
- [ ] Scraped slots carry `clinic_slug` matching their clinic's config
- [ ] New migration adds a nullable `slots.clinic_slug`. A migration test
      upgrades a database from the previous version, and old rows read back
      with no slug without errors
- [ ] Storage round trip: a slot written with a slug reads back with the same slug
- [ ] `/api/availability` slots include `clinic_slug`
- [ ] Frontend `Slot` type and mock envelopes include `clinic_slug`; vitest
      and the build pass
- [ ] `pytest` passes; `migrate.py` applies cleanly to a copy of the local DB
- [ ] No deduplication behaviour changed (the API's existing dedupe key is untouched)

## Blocked by

None - can start immediately

## User stories addressed

- User story 10
- User story 11
- User story 41
- User story 42
- User story 43
