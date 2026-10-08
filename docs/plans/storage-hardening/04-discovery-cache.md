# Implementation plan — Slice 4: discovery cache (SHELVED)

Decisions: `docs/plans/storage-hardening/decisions.md` (item 7).
Builds on slices 1-3. Migration 3. No frontend or API change.

Status: **shelved 2026-10-08.** Step 0 showed the homepage request can't be
skipped, and a second spike measured what the cache would still save (below).
The rest of this file is kept as the record of the design.

**Measured saving (2026-10-08, all 28 clinics, discovery only):** 32
discovery requests per run (28 homepages + 4 location pages, from A Balanced
Body, Tall Tree Health, Equilibrium Massage Therapy, Victoria Massage
Therapy); 47.9s network, ~6.5s of it location pages; parsing 0.25s total;
10.1MB downloaded. A cache saves the 4 location pages and the parsing: about
7s and 4 requests per run (~384 requests/day). Not worth it.

## Goal

Stop re-discovering every clinic's Jane setup on every run. Today each
clinic scrape fetches the clinic homepage (sometimes up to 3 location pages
too), parses `routerOptions`, and rebuilds the service map and staff lookup,
every 15 minutes, although that setup changes rarely. Cache it per clinic in
SQLite and reuse it until one of the decided invalidation rules fires.

Why it matters: fewer requests to Jane's unofficial endpoints (being gentle
matters more than speed, see the sequential-scraping note in
`decisions.md`), and shorter runs, which buys headroom before multi-city
runs approach the 15-minute interval.

## Step 0: does the openings API need the homepage's cookies?

`_fetch_router_options` says Jane sets cookies on the homepage that the
openings API requires, so the same session is used for both. If that is true,
a cached clinic still needs the homepage request just for its cookies, and
the cache only saves parsing and the location-page fallbacks: most of the
request saving disappears.

Spike (no code change, a handful of requests to one clinic, the same traffic
the scraper already sends): call `/api/v2/openings/for_discipline` for a
known treatment with (a) a fresh session that never loaded the homepage and
(b) a session that did. Compare status and body. Record the result here.

**Result (2026-10-08, Geometry, treatment 1):** (a) cold session → 403
Forbidden; (b) after loading the homepage (cookies `_front_desk_session`,
`jane_device`) → 200 with 3 openings. The homepage request is required on
every scrape regardless of caching. The remaining saving is parsing
(negligible) and location-page fallback fetches. Caching the cookies
themselves was rejected (session tokens in the DB; Jane rotates
`_front_desk_session` on each response; works around Jane's access gate).
Decision: shelved (see status above).

- If (a) works: the cache skips the homepage entirely. Plan as below.
- If (a) fails: decide whether the slice is still worth it (it would save
  parsing plus location-page fetches for the few clinics that need them),
  or whether a cheaper cookie request exists. Revisit before building.

## Rules (from decision 7)

- Table `clinic_discovery`: `subdomain` (primary key), `service_map` JSON,
  `staff_lookup` JSON, `config_hash`, `discovered_at` (ISO 8601, UTC).
- An entry is dropped when:
  1. it is older than `DISCOVERY_TTL_HOURS` (default 24);
  2. an openings call for the clinic returns non-200;
  3. a returned slot has a `staff_member_id` missing from the lookup;
  4. the hash of the clinic's service config no longer matches (editing
     `clinics.py` takes effect on the next scrape).
- An empty openings list does NOT invalidate (normal for a clinic with no
  openings; the intermittent-empty TODO in `janeapp.py` is separate).

## Decisions taken in this plan (flagged for review)

- **SQL stays in Storage.** `get_discovery(subdomain)`,
  `save_discovery(subdomain, service_map, staff_lookup, config_hash,
  discovered_at)`, `drop_discovery(subdomain)`. The TTL check is done in
  Python on the single row's `discovered_at` (one row, so no SQL time
  comparison needed).
- **The adapter never imports Storage.** `run_all` takes an optional
  `discovery_cache` and passes it to `adapter.fetch_availability(clinic,
  cache)`. `None` means today's behaviour, so existing tests and the
  adapter's statelessness are unchanged. The cache interface is the three
  Storage methods above (tests can pass a dict-backed fake).
- **Failed discovery is never cached** (`discover()` returned `{}`). A
  successful discovery with an empty service map IS cached: it is a real
  answer (the config matches nothing), and the config hash drops it when
  `clinics.py` is fixed.
- **Serialisation.** `service_map` keys are `ServiceType` enums; stored by
  `.value` and mapped back on read. `staff_lookup` keys are ints in Python
  but strings in JSON; converted back on read (otherwise every lookup misses
  and rule 3 fires on every slot).
- **Config hash** = SHA-256 of the clinic's `services` serialised with sorted
  keys (enums by value), plus the subdomain.
- **Migration 3** creates the table only. A missing or stale table entry just
  means "discover", so the deploy needs no backfill.

## Open questions (need your call)

1. **Step 0 spike.** OK to run it now (a few live requests to one clinic)?
2. **What happens to the current scrape when an entry is invalidated
   mid-scrape** (rules 2 and 3)?
   - (a) Rediscover immediately and retry that clinic once in the same run.
     Recommended: a new RMT would otherwise show as "Unknown" for a whole
     interval, which today never happens, and a stale-cookie or changed-ID
     failure would cost a full interval of that clinic's slots.
   - (b) Drop the entry and keep this run's results as they are; the next
     run rediscovers.
3. **Changes to adapter code** (e.g. `SERVICE_TYPE_KEYWORDS` or
   `_map_services` logic) are not in the clinic config, so the hash would
   not catch them; only the 24h TTL would.
   - (a) Add a `DISCOVERY_VERSION` constant to the hash, bumped by hand when
     mapping logic changes. Recommended: explicit, one line.
   - (b) Rely on the TTL (up to 24h of stale mapping after a deploy).
   - (c) Clear the table on every deploy.

## Files to touch (assuming step 0 passes and the recommendations)

- `backend/storage.py`: migration 3; the three cache methods.
- `backend/config.py`: `discovery_ttl_hours()`.
- `backend/scraper/adapters/janeapp.py`: use the cache in
  `fetch_availability`; invalidation on non-200 and unknown staff;
  `config_hash()` helper.
- `backend/scraper/runner.py`: optional `discovery_cache` passed through.
- `backend/main.py`: pass `Storage` as the cache.
- Tests: Storage round-trip and migration; adapter behaviour with a fake
  session (canned `routerOptions` page and openings JSON, no live network)
  and a fake cache; runner pass-through.

## TDD sequence (draft, finalised after the questions)

1. Migration 3 creates `clinic_discovery`.
2. `save_discovery` / `get_discovery` round-trip, including enum keys and
   int staff ids surviving JSON.
3. `drop_discovery` removes the entry.
4. `config.discovery_ttl_hours()` default and env var.
5. Adapter with an empty cache discovers and saves.
6. Adapter with a fresh, matching entry skips discovery (no homepage
   request on the fake session).
7. Expired entry (TTL) is rediscovered.
8. Config hash mismatch is rediscovered.
9. Openings non-200 drops the entry (+ retry, per question 2).
10. Unknown `staff_member_id` drops the entry (+ retry, per question 2).
11. Empty openings list keeps the entry.
12. Failed discovery is not cached.
13. `run_all` passes the cache through; `main.scrape_city` supplies Storage.

## Risks

- **Step 0** may shrink the benefit a lot (see above).
- **Stale data between invalidations.** A renamed RMT keeps the old name
  until the TTL; a removed treatment keeps being queried until its openings
  call fails. Both are bounded by the 24h TTL.
- **Concurrency.** Single writer today (sequential scheduler). If scraping
  goes parallel, two clinics never share a subdomain, so entries don't
  collide.

## Manual checklist

To be written once the plan is final.
