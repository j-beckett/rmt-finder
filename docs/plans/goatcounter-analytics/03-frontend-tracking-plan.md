# Implementation plan — Slice 03: frontend tracking

Issue: `docs/plans/goatcounter-analytics/03-frontend-tracking.md`
Status: committed 2026-10-09; dev-server, blocked-script and README-render checks pending (see issue).

## Verified against GoatCounter v2.7.0 (2026-10-09)

Sources: `public/count.js`, `hit.go`, `handlers/backend.go` and
`handlers/handlers.go` at tag `v2.7.0` on github.com/arp242/goatcounter;
goatcounter.com/help/js, /help/events, /help/campaigns.

- **Tag:** `<script data-goatcounter="https://stats.studiobeckett.ca/count"
  data-goatcounter-settings='{"no_onload": true}' async
  src="https://stats.studiobeckett.ca/count.js">`. The endpoint is `/count`
  (GET and POST routes in `backend.go`); a self-hosted instance serves its
  own `/count.js` from the embedded `public/` dir (`handlers.go`).
- **On-load counting off:** `no_onload: true` in `data-goatcounter-settings`.
  It also skips auto-binding of `data-goatcounter-click` events (help/js).
- **`count(vars)`:** `{path, title, event, referrer}`. Event paths must not
  start with `/` (help/events); the server strips it anyway (`hit.go`).
- **`window.goatcounter`:** absent until the script runs (the script does
  `window.goatcounter = window.goatcounter || {}`), then has `count()`. With
  `async` it may load after the app calls it (help/js suggests polling).
- **Campaigns survive a custom path:** `count()` always sends
  `q: location.search` separately, and the server reads `utm_campaign` /
  `utm_source` from `q` for page views (`hit.go`). So we pass a clean path and
  campaigns still work.
- **Free extras:** `count()` refuses localhost, private IPs (`192.168.*`,
  `10.*`) and `file:` (`filter()`), a second guard for `vite preview` and LAN
  phone testing. It also honours GoatCounter's own `skipgc` storage flag.

## Decisions

- **Production only:** a small Vite plugin in `vite.config.ts` with
  `apply: 'build'` injects the tag via `transformIndexHtml`. `npm run dev`
  never sees it. `vite preview` serves the build but from localhost, which
  `count.js` refuses; the wrapper also checks `import.meta.env.PROD`.
- **`async`, not blocking:** a hung stats host must never delay the page. If
  the app sends a hit before the script has run, the wrapper waits for the
  script element's `load` event once; if it errors, the hit is dropped.
- **Page-view raw city:** the unknown-city title uses the URL's `?city=` as
  typed (the app lowercases it for the request).
- **Slot without a slug** (pre-migration run): no Book-click hit. An
  undercount, the safe direction.
- **Trackable click:** `click` with button 0 (tap, Ctrl/Cmd-click, keyboard
  Enter) or `auxclick` with button 1 (middle). Everything else, no.
- **Opt-out key:** `localStorage['rmt-notrack'] = '1'`. Read once per page
  load at module init (`?notrack` arrives with a full page load).

## Modules

- `src/lib/analytics.ts` (pure): `pageView(state, search)`,
  `bookClick(slot)`, `isTrackableClick(event)`, `optedOut(search, getStorage)`.
- `src/lib/tracker.ts`: `createTracker({ production, optedOut, win })` →
  `send(hit)`. No-op when not production, opted out, or script absent; waits
  for the script's `load` if the element is there but not run yet; never
  throws.
- `src/lib/track.ts` (glue, untested): builds the singleton from `window`,
  `import.meta.env.PROD` and `optedOut(location.search, () => localStorage)`.

## Wiring (thin)

- `App`: `useEffect(() => { const hit = pageView(state, location.search);
  if (hit) send(hit) }, [state])`. `state` changes only when a fetch settles
  (or goes to loading, which yields no hit): first load, city switch,
  Back/Forward.
- `SlotCard`: `onClick` and `onAuxClick` call `trackBookClick(slot, event)`.
  No `preventDefault`; `href`, `target="_blank"` and `rel` unchanged.

## Steps (vitest, one test at a time, red then green)

1. `pageView`: ready state → `/<served city>` with the city name title
   (default city with no `?city=`, switched city, Back/Forward = same rule).
2. `pageView`: tracking params in `search` never reach the path.
3. `pageView`: unknown city → `/unknown-city`, raw value in title only.
4. `pageView`: API/network error and loading → no hit.
5. `bookClick`: `book/<slug>`, clinic name title, `event: true`; null slug →
   no hit.
6. `isTrackableClick`: left yes, middle `auxclick` yes, right no.
7. `optedOut`: `?notrack` sets + returns true; persists on a later plain
   load; `?notrack=off` clears; throwing storage → false.
8. `createTracker`: calls `count()` with the hit; no-op when opted out, not
   production, script absent; waits for script `load`; swallows a throwing
   `count()`.
9. Wiring, Vite plugin, README. Check `npm run build` output and dev-server
   network traffic by hand.
