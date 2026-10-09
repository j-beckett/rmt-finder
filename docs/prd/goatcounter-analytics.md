# PRD — Traffic Analytics with Self-Hosted GoatCounter

Consolidates the decisions resolved via grill-me on 2026-10-09. The tool
choice (GoatCounter, self-hosted on the existing droplet, over goatcounter.com
or a home-built tracker) was settled on 2026-10-08 and is not re-opened here.

## Problem Statement

RMT Finder is live in two cities (Victoria, Langford & West Shore), but the
site owner has no idea whether anyone uses it. There is no answer to:

- How many people visit, and which city do they look at?
- Where do visitors come from (search, social, a shared link)?
- Are visitors on phones or desktops?
- Most importantly: **which clinics does RMT Finder actually send people to?**

That last question is the one with future value. A possible revenue idea is
featured placement for clinics, and the only credible pitch is evidence:
"RMT Finder sent your clinic N booking clicks last month." That number has to
be trustworthy — not inflated by the owner's own testing, bots, or local
development — and it has to stay attached to the right clinic even when the
clinic's display name is edited.

There is also a gap underneath the metric: clinics have no stable identity.
Everything — storage, API, frontend — knows a clinic only by its display
name, which is meant to be edited freely. Any long-lived per-clinic metric
keyed on the name would split its history on every rename.

Finally, this is a portfolio piece for a data-engineering role. The analytics
should show deliberate metric design (one key metric, clean keys, misleading
metrics consciously dropped) and sound ops (versioned config, a runbook,
resource limits, an upgrade and rollback path) rather than a pasted snippet.

## Solution

A self-hosted GoatCounter instance at `stats.studiobeckett.ca`, running as a
memory-capped systemd service on the existing droplet behind Caddy, with a
private dashboard. The frontend loads GoatCounter's script in production only
and sends exactly two kinds of hit:

1. **City page views** — one per city actually shown, under a clean path
   (`/victoria`, `/langford`), sent once the API answers. Unrecognized
   `?city=` values are grouped under one `/unknown-city` row.
2. **Book clicks** — one per click on a slot card, keyed by a new stable
   per-location clinic slug (`book/<slug>`) with the clinic's display name as
   the label.

Every clinic gets a fixed `slug` in the clinic config, carried through the
scraper, storage and API to the frontend, so the key survives renames. The
owner opts their own devices out once each via `?notrack`. All server config
(systemd unit, the full Caddyfile) lives in the repo, guarded by pytest checks,
with a step-by-step runbook the owner executes on the droplet.

From the dashboard the owner can see total page views and unique visitors,
views per city, referrers and campaigns, devices/browsers/screen sizes and
locations, and Book clicks per clinic — with the device breakdown filterable
to Book clicks alone.

## User Stories

### Site owner — reading the numbers

1. As the site owner, I want to see total page views and unique visitors over any date range, so that I know whether people use RMT Finder at all.
2. As the site owner, I want page views broken down by city, so that I can see which city gets used and where to add clinics or promote.
3. As the site owner, I want a visit with no `?city=` to count under the city the app actually showed, so that default-city traffic isn't a separate, confusing row.
4. As the site owner, I want switching city and Back/Forward between cities to count as views of the new city, so that city counts reflect what people actually looked at.
5. As the site owner, I want tracking parameters (`fbclid`, `utm_*`) kept out of page-view paths, so that one city doesn't fragment into many rows.
6. As the site owner, I want `utm_*` campaign tags still recorded as campaigns, so that I can measure a deliberate promotion.
7. As the site owner, I want to see referrers, so that I know which sites and shares bring visitors.
8. As the site owner, I want visits to unrecognized city links grouped into a single row with the bad value visible, so that I can spot a broken shared link without the dashboard filling with junk rows.
9. As the site owner, I want Book clicks counted per clinic location, so that I know which clinics RMT Finder sends people to.
10. As the site owner, I want each clinic's Book-click history to survive edits to its display name, so that the numbers I'd show a clinic are continuous.
11. As the site owner, I want locations of a multi-location business to share a key prefix, so that I can filter the dashboard to the whole business and still see each location separately.
12. As the site owner, I want to filter the device, browser and screen-size panels to Book clicks only, so that I know whether bookers are on mobile or desktop.
13. As the site owner, I want every click counted (no deduplication), so that the counts are honest raw events; unique visitors are available separately.
14. As the site owner, I want middle-clicks counted as Book clicks, so that desktop users who open cards in new tabs aren't missed.
15. As the site owner, I want a known, consistent undercount rather than any overcount, so that numbers shown to a clinic are a defensible minimum.

### Site owner — keeping the numbers clean

16. As the site owner, I want to opt each of my browsers out once by visiting a link, so that my own heavy use doesn't inflate the stats.
17. As the site owner, I want that opt-out to persist across deploys, so that I don't have to redo it every time I ship.
18. As the site owner, I want a way to turn tracking back on for a browser, so that I can test tracking without an incognito window if I prefer.
19. As the site owner, I want local development, `vite preview` and LAN phone testing to send nothing, so that dev traffic never reaches the stats.
20. As the site owner, I want the analytics script not loaded at all outside production builds, so that dev mode makes no requests to the stats host.
21. As the site owner, I want visits where the API failed not counted, so that outages don't masquerade as visitor behaviour.
22. As the site owner, I want bots handled by GoatCounter's built-in filtering plus the fact that every hit requires JavaScript or a real click, so that I get clean data without maintaining bot rules.
23. As the site owner, I want a short "what looks wrong" checklist in the runbook, so that I can recognize bot or tracking anomalies if they appear.

### Site owner — privacy and access

24. As the site owner, I want the dashboard private by default, so that per-clinic click counts — the thing I might sell — aren't public.
25. As the site owner, I want to be able to create a revocable view-only link, so that I can show a reviewer the live dashboard during a job application.
26. As the site owner, I want the analytics cookieless and self-hosted, so that no consent banner is needed and the data stays mine.

### Site owner — operating it

27. As the site owner, I want a step-by-step runbook in the repo, so that I can set up the server myself (Claude cannot SSH to the droplet).
28. As the site owner, I want the runbook to tell me exactly when to add the DNS record and wait for it, so that Caddy can obtain the TLS certificate on the first try.
29. As the site owner, I want a memory check before and after install, so that I know the 512MB droplet still has headroom.
30. As the site owner, I want GoatCounter memory-capped, so that if it misbehaves it is the one killed, never the site.
31. As the site owner, I want GoatCounter reachable only through Caddy, so that it isn't exposed directly to the internet.
32. As the site owner, I want the full Caddyfile versioned in the repo, so that the droplet can be rebuilt from the repo plus the runbook.
33. As the site owner, I want the runbook to diff the live Caddyfile against the repo before copying, so that a manual server edit is noticed instead of overwritten.
34. As the site owner, I want config validated before reload, so that a typo can't take down the main site.
35. As the site owner, I want the GoatCounter version pinned and recorded in one place, so that I always know what is running.
36. As the site owner, I want a documented upgrade procedure with explicit migrations and a one-command rollback, so that upgrades are deliberate and reversible.
37. As the site owner, I want a smoke test that proves both opt-out and tracking work, so that I know the feature is live and correct after setup.

### Visitor

38. As a visitor, I want the page to work exactly the same if the analytics script is blocked or fails to load, so that tracking never breaks booking.
39. As a visitor, I want clicking a slot card to open the booking page immediately, so that tracking adds no delay.
40. As a visitor, I want no cookies and no personal data collected, so that using RMT Finder doesn't track me across the web.

### Developer / agent maintaining the project

41. As a developer, I want every clinic to have a required, unique, well-formed slug enforced by tests, so that a copy-pasted clinic entry with a duplicate slug fails CI.
42. As a developer, I want the slug stored on each slot and returned by the API, so that every layer can rely on a stable clinic key (including future slot-lifetime analytics).
43. As a developer, I want the schema change delivered as a new migration following the project's rules, so that deploys stay safe.
44. As a developer, I want the tracking decisions in pure, unit-tested functions, so that the rules are verified without a browser or a real GoatCounter.
45. As a developer, I want pytest checks that GoatCounter's listen address, memory cap and Caddy proxy port agree, so that config drift is caught before it reaches the server.

### Portfolio reviewer

46. As a portfolio reviewer, I want the README's "How it works" diagram and prose to show the analytics, so that I can see the metric design and ops choices.
47. As a portfolio reviewer, I want the reasoning for dropped metrics recorded, so that I can see the metrics were chosen deliberately, not by default.

## Implementation Decisions

### Clinic identity

- `ClinicConfig` gains a required `slug`: a fixed, hand-maintained string,
  never derived from the name at runtime.
- One slug per **location** (per config entry), not per business. Locations of
  one business share a prefix (e.g. `equilibrium-fisgard`,
  `equilibrium-tillicum`). No separate parent/group field.
- Format: lowercase letters, digits and hyphens. Unique across all cities.
- Initial values: Claude generates a draft list from current names; the owner
  reviews and shortens before they are committed as literals.
- The Jane subdomain is not used as the key: it is shared across locations
  (Equilibrium) and owned by the platform.

### Slug through the pipeline

- The `Slot` model gains `clinic_slug`, set by adapters from the clinic config
  alongside `clinic_name`.
- New migration appended to `MIGRATIONS`: a nullable `clinic_slug` column on
  `slots`. Historical rows stay NULL; the API serves only the latest run per
  city, so served slots carry a slug from the first post-deploy scrape.
- The API's slot serialization already emits every `Slot` field, so the API
  response gains `clinic_slug` without a contract change elsewhere.
- The frontend `Slot` type gains `clinic_slug`.

### Event contract (GoatCounter paths and titles)

| Hit | Path | Title | When |
|---|---|---|---|
| City page view | `/<servedCity>` | city display name | API answered successfully: first load, city switch, Back/Forward |
| Unknown city | `/unknown-city` | `unknown city: <raw value>` | API reported an unknown city |
| (none) | — | — | API/network error |
| Book click | `book/<clinic_slug>` | clinic display name | primary click or middle-click on a slot card |

- `servedCity` is the city the API reports serving, not the URL value, so the
  backend's default city is respected automatically.
- The automatic on-load page view is disabled; the frontend sends page views
  itself with the normalized path.
- Book clicks: `click` (covers tap, Ctrl/Cmd-click, keyboard Enter) plus
  `auxclick` filtered to the middle button. Right-click / long-press "open in
  new tab" is accepted as an untracked undercount.
- No deduplication of clicks or views.
- The slot card's link behaviour (new tab, `noopener noreferrer`) is
  unchanged; tracking must never block or delay navigation.

### Frontend modules

- **Analytics core (deep module, pure functions):** page-view decision from
  app state; Book-click event from a slot; trackable-click test from a mouse
  event; opt-out handling from the query string and a storage object.
- **Tracker wrapper (thin):** sends hits via GoatCounter's `count()`. It is a
  no-op when opted out, when the script is absent (blocked, failed, or dev),
  and outside production builds. It never throws.
- **Wiring:** the app sends a page view when the availability state settles,
  and slot cards attach the click handlers. Kept thin; logic stays in the
  modules above.
- **Script loading:** GoatCounter's script, served from
  `stats.studiobeckett.ca`, is included only in production builds.

### Owner opt-out

- `?notrack` sets a persistent flag in the browser's local storage; while set,
  nothing is sent. `?notrack=off` clears it.
- Once per browser/device; survives deploys. Lost only by clearing site data,
  a new browser, or incognito (which is the intended testing path).
- Storage access is wrapped so a blocked or throwing storage never breaks the
  page (it then behaves as not opted out).

### Server

- **Host:** `stats.studiobeckett.ca` (A record at Namecheap, added by the
  owner). Chosen domain-wide so other Studio Beckett sites can be added to
  the same instance later.
- **Process:** GoatCounter binary as a systemd service, listening on
  `127.0.0.1` only (a port distinct from the API's), `MemoryMax=128M`,
  restart on failure, its SQLite database in a dedicated data directory.
- **Caddy:** the full Caddyfile (existing `rmtfinder.` block plus a new
  `stats.` block reverse-proxying to GoatCounter) is versioned in the repo.
  Rule: change in the repo, then copy to the server — never edit only on the
  server.
- **Dashboard:** private (login), with a view-only secret link created only
  when needed.
- **Memory:** measured 2026-10-09 at 244MB available of 458MB, with 1GB swap
  already present. GoatCounter (~30–60MB expected) fits; no resize and no
  swap step.
- **Upgrades:** manual and pinned. Version recorded in one place in the repo.
  Versioned binaries side by side with a symlink; upgrade = back up DB file,
  install new binary, stop, run migrations explicitly, switch symlink, start,
  smoke test. Rollback = point the symlink back. No automatic migration on
  start. Exact CLI commands are verified against GoatCounter's documentation
  when the runbook is written, not assumed.

### Deploy-config tests (pytest)

Following the existing deploy-script test pattern, assert that:

- GoatCounter's unit listens on `127.0.0.1` only and sets a memory cap.
- The Caddyfile's `stats.` block proxies to the same port the unit listens on.
- The existing `rmtfinder.` block still proxies to the API port.

### Runbook (owner executes)

A step-by-step document in `docs/plans/` covering: memory check; DNS record
and waiting for resolution; installing the pinned binary; creating the data
directory and service; diff-validate-copy-reload of the Caddyfile; creating
the site and user; one-time `?notrack` on each owner device; smoke test
(opt-out browser sends nothing, incognito sends a city view and a Book click,
device filter works on `book/`); post-install memory check; the upgrade and
rollback procedure; the "what looks wrong" checklist (spike from one referrer
or screen size; Book clicks without matching city views).

### Docs

- README "How it works": add a GoatCounter node to the diagram (frontend →
  self-hosted GoatCounter: city views, Book clicks) and a short paragraph:
  self-hosted and cookieless, what is tracked and why, owner traffic opted
  out. The dashboard is not linked.
- No analytics notice on the site itself.

### Suggested slicing (for prd-to-issues)

1. Clinic slugs end to end (backend, pytest) — independently useful.
2. GoatCounter server setup: unit, Caddyfile, deploy-config tests, runbook —
   owner runs the server steps. Independent of slice 1.
3. Frontend tracking (vitest, against a fake `count()`) — can be built before
   slice 2 is live; needs slice 1 deployed for real slugs.
4. README update and end-to-end smoke test once 1–3 are deployed.

## Out of Scope

- **Empty-results tracking** ("Nothing left today" / "No openings right now").
  Dropped: Today is the default view, so evening visits always hit an empty
  Today, and quiet days reflect clinic hours rather than demand. Unmet demand
  is better answered later by joining page views with scrape-DB slot counts
  (recorded in NOTES.md).
- **Footer-link tracking** (main site, Buy Me a Coffee). Buy Me a Coffee
  reports real supporters; studiobeckett.ca's own stats would show RMT Finder
  as a referrer. Revisit only with a concrete decision it would inform.
- **A city-switch event** distinct from page views.
- **A `/go/<slug>` redirect** to capture right-click/long-press opens. Revisit
  if a clinic disputes or pays based on the numbers.
- **A parent/group field** for multi-location businesses. Revisit when a
  multi-location business becomes a featured-placement customer.
- **Making the slug the clinic's primary identity** throughout storage
  (replacing `clinic_name` as the key). Revisit with slot-lifetime analytics.
- **Proxying the counting endpoint through the app's own host** to evade
  blockers. Fallback only if numbers look suspiciously low.
- **IP-based exclusion** in GoatCounter settings (optional extra, not required).
- **Per-clinic reports** for featured placement (exports, clinic-facing views).
- **Backups** of the GoatCounter database — see Further Notes.
- **The Studio Beckett footer** — a separate feature.
- **An on-site analytics/privacy notice.**

## Further Notes

- **Backups are the next feature and a hard dependency.** Unlike the main
  database (which the next scrape repopulates, losing only history), analytics
  history cannot be rebuilt. Nightly backups of *both* SQLite databases follow
  immediately after this feature. Candidate approach to grill: DigitalOcean
  Droplet Backups plus a `sqlite3 .backup` copy beforehand (live-disk
  snapshots of SQLite are usually but not guaranteed consistent; restores are
  whole-droplet). Accepted risk: a few weeks of early, low-volume stats.
- **Footer follow-up:** "built by Studio Beckett", logo, main-site link, maybe
  Buy Me a Coffee; design chosen together from options. The main-site link
  must not use `noreferrer`, or studiobeckett.ca's stats won't see RMT Finder
  as the referrer.
- **Adding studiobeckett.ca later:** each additional site in the same
  GoatCounter instance typically gets its own hostname; nothing here blocks it.
- **Verified facts relied on** (checked 2026-10-09 against GoatCounter's
  `count.js` and changelog): default path is `pathname + search`; the script
  skips localhost and private IPs; automatic counting can be disabled;
  `count()` accepts path, title and an event flag; the dashboard path filter
  also filters browser/system/size/location panels (since v2.0); bot hits go
  to a separate table (v2.7). Latest release at time of writing: v2.7.0.
- **Undercount sources, by design:** right-click/long-press opens, privacy
  blockers, visits during API outages. All bias numbers downward, which is the
  safe direction for figures shown to clinics.
