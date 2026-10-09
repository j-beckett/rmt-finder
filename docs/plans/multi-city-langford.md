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

## Found while testing (not fixed here)

- The Jane adapter hardcodes `location_id=1`. Kari Lund's location isn't 1,
  so its openings call returns 404 and it shows no slots. Multi-location
  accounts (Thetis has two) only get location 1 scraped.
