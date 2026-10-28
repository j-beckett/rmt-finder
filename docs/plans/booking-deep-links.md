# Implementation plan — Booking deep links

Status: built 2026-10-28, awaiting the user's manual check before commit.

## Goal

"Book" should land the user on the RMT's 60-min calendar, not the clinic's
Jane homepage where they still have to find the practitioner and treatment.

## Decisions (2026-10-28)

- **Link to practitioner + treatment.** Jane's
  `<booking page>#/staff_member/S/treatment/T` opens that RMT's calendar for
  that treatment with times showing. Checked in the browser on every URL
  shape in the roster: plain subdomain (Geometry, Active Health), a
  multi-location account (Equilibrium Tillicum), one-location-per-RMT
  (Victoria Massage Therapy), a shared physio account (Natural Balance) and
  a `/locations/` page (Tall Tree). An unknown staff ID falls back to the
  clinic homepage, so a bad link is no worse than today.
- **Fallback when the RMT is unknown:** `#/discipline/D/treatment/T`, the
  treatment's calendar for all its RMTs.
- **Dedup keeps the Initial row.** `api._dedupe_slots` already collapses one
  opening listed under an "Initial" and a plain treatment, keeping the
  first. Once each row links to its own treatment, which row survives
  decides where the user lands. The app is aimed at people looking for a
  new RMT, so prefer the row whose treatment is named as a first visit.
  Jane lists Initial first at every affected clinic today (Equilibrium,
  The Lab, Heart of the Village, Pearl), so this pins the current behaviour
  rather than changing it.
- **Not a filter rule.** Dropping plain 60s at clinics that have an Initial
  one would hide RMTs who aren't on the Initial treatment (Cheri Moore at
  Massage Therapy Group, Gary Johnson at Equilibrium Fisgard).
- **`surgical` joins the shared excludes** (Atlas "Pre/Post Surgical
  Registered Massage Therapy").
- **No migration.** `booking_url` is already stored per slot; old runs keep
  their clinic-level links until the next scrape replaces them.

## Steps

1. `clinics.py`: add `"surgical"` to `EXCLUDED_TREATMENT_KEYWORDS` (test in
   `test_treatment_filter.py`).
2. `janeapp.py` `_fetch_openings`: build the per-slot URL from the booking
   page, staff ID and treatment (tests in `test_janeapp_locations.py`).
3. `api.py` `_dedupe_slots`: keep the first-visit row when two collapse
   (test in `test_api.py`).

## Noticed, not in scope

- Geometry treatment 426 is a second "60-Minute RMT Session" for one RMT
  who isn't taking new general-massage patients; no openings through
  Dec 26. Same name as the main one, so only a per-clinic treatment-ID
  exclude could drop it.
- 9 of 19 Langford clinics returned no openings over 7 days on 2026-10-28;
  may be real or the empty-response TODO in `janeapp.py`.
