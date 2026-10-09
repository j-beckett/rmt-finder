# Implementation plan — Multi-city: Langford & West Shore

Status: built 2026-10-08, awaiting the user's manual check before commit.

## Goal

Add a second city. The backend already scrapes and serves per city (the
scheduler, `?city=` and timezones all key off the clinic roster), so the
work is the roster, display names, a city list for the frontend, and the
picker.

## Decisions (2026-10-08)

- **One city key `langford`, displayed "Langford & West Shore".** It
  includes the Colwood clinics on Wale Rd and Sooke Rd: they advertise to
  Langford, sit 5 minutes away, and the line between the two towns doesn't
  match how people search.
- **Specialty exclusions go in the shared list.** Treatments the shared
  keywords missed (buccal, IASTM, mastectomy, breast, abdominal, C-section,
  child, VA, return visit, non-registered) are never general RMT slots, so
  they're excluded everywhere. The first plan was per-clinic excludes, but
  then a Victoria clinic that later added buccal would leak. The global
  version also fixed three leaks already in Victoria results (Glow
  non-registered; Equilibrium and Pearl return visits). `extra_excludes` is
  now only for terms that are wrong at one clinic. The cases are in
  `tests/test_treatment_filter.py` and are seed data for the LLM classifier.
- **The `?city=` URL param is the source of truth.** A shared link
  preloads that city. Changing city uses `history.pushState`: no reload,
  and Back returns to the previous city. An unknown `?city=` shows "We
  don't cover X yet".
- **City switcher: a "Change city" pill under the intro.** The heading
  already names the city, so the pill needs no prompt text. A
  "Not in Langford?" label beside it read as a stray caption, and a corner
  button would sit above the heading on phones. It's a custom menu, not a
  native select, so the open list matches the site (cream card, forest
  border, offset shadow). Lime is kept for active and book actions, so the
  current city is marked with a checkmark, and hover is a darker cream.
  Keyboard behaviour (`lib/menu.ts`) follows the WAI-ARIA select-only
  combobox pattern.
- **Jane only.** Non-Jane Langford clinics are booked by phone or through
  Medimap's booking button, which hides the system behind it. That leaves
  nothing to build an adapter against.

## Roster (verified 2026-10-08 against the live Jane pages)

thetismassage, westshoremassagetherapy, aurorahealthclinic, alignhealth,
driftwoodhealth (the same account as victoriasportstherapy),
lucidintegrativehealth, eileendurantregisteredmassagetherapy,
storyanddepthmassage, sanctumwellness, symmetryco, synctherapy,
karilundrmt.

## Steps

1. Test: every roster city has a `CITY_TIMEZONES` row. Add Langford.
2. Test: `config.city_name()` returns the display name, falling back to
   title case.
3. Test: `GET /api/cities` lists `{slug, name}` for the roster's cities,
   sorted.
4. Test: the envelope carries `city` and `city_name`, so the title follows
   the URL.
5. Add the 12 clinics to `clinics.py`. Test the shared excludes with real
   names, then move the specialty keywords into the shared list.
6. Frontend: `lib/city.ts` URL helpers (vitest first), the `fetchCities` and
   city-aware `fetchAvailability` API calls, and `CityPicker` in the heading.

## Jane locations (fixed 2026-10-08)

The adapter used to hardcode `location_id=1`. Jane requires the id, and a
wrong one gives a 404 (Kari Lund is #2, Metchosin #3) or another location's
openings (Natural Balance is #4 in an account whose #1 is Saanichton). It now
reads `App.location_id` from the booking page on every scrape. Multi-location
accounts name their location by URL slug (`jane_rmt(..., location=...)`), and
an account with several locations and no slug fails loudly instead of
guessing. Three Victoria accounts turned out to be multi-location:
Equilibrium (3 sites), Victoria Massage Therapy (one "location" per RMT;
Noelle Daigle, #11, had never been scraped) and A Balanced Body (clinic plus
yoga studio).

## First visits booked as 70-75 min (2026-10-08)

Some clinics book a new patient's first visit as 70-75 min (a 60-min
massage plus an assessment) and have no 60-min option a new patient can
book: Christina Baptista, Maggie Kay and Ocean View. Rule: 60 min as
before; **only if a clinic has no accepted 60-min treatment**, accept 70-75
min treatments named as a first visit ("initial", "first visit", "new
patient"). Shared excludes still apply. 43 of 46 clinics also have 75-min
treatments, and 10 have a 75-min "initial" next to their 60s. Taking those
too would list each opening twice (as a 60 and a 75), so the fallback never
runs when a 60 exists. A guard test pins this, and was mutation-checked to
fail when the rule is loosened. Live check: no opening listed twice in either
city, apart from Massage Therapy Group's known same-length double listing,
which the API's `_dedupe_slots` already collapses.
