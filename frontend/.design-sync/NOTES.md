# design-sync notes (rmt-finder frontend → Claude Design "RMT Finder")

This is an app, not a published library: there's no dist build, no Storybook and no `.d.ts` tree. The sync is held together by these durable inputs:

- `entry.ts`: library entry re-exporting the 5 components. Don't let the converter synthesize from `src/`, because `main.tsx` mounts the app on import.
- `tsconfig.json`: comment-free alias config. The converter's tsconfig comment-stripper treats the `/*` in `"@/*"` as a block comment and eats `paths` in `tsconfig.app.json`, so `@/lib/...` imports fail to resolve.
- `tailwind.css` + `build-css.mjs` (= `cfg.buildCmd`): Tailwind v4 must be compiled first. The input imports `src/index.css` and adds an `@source inline()` safelist so the design agent gets theme/layout utilities the app doesn't use yet. `build-css.mjs` strips `@font-face` (inlined fontsource rules keep relative `./files/` urls that break); fonts ship via `cfg.extraFonts` instead.
- `cfg.dtsPropsFor`: hand-written prop contracts. The components type props inline, so auto-extraction gives `[key: string]: unknown`.
- Converter deps are isolated in `.ds-sync/`: esbuild, ts-morph, @types/react, `@tailwindcss/cli@4.3.2` (keep in step with the app's tailwindcss), playwright + chromium.

Build order: `node .design-sync/build-css.mjs`, then `package-build.mjs --config .design-sync/config.json --node-modules ./node_modules --out ./ds-bundle` (no `--entry`; `cfg.entry` handles it), then validate.

- Previews use time-relative mock data (dates computed in America/Vancouver, fixed clock times) so the Today/Tomorrow pills line up. The capture harness freezes the clock, so sheets show a fixed date.
- Availability previews: keep each story to ≤3 slot cards (≤2 with the banner or day badges). Longer stories clip at the card's height cap.
- CityMenu's open listbox is internal state (no prop), so it can't render statically and isn't previewed.
- `SlotCard` is exported from `SlotList.tsx` (2026-10-20) so the agent can place a single card; it is listed in `entry.ts` alongside `SlotGroups`.
- Tailwind auto-scans cwd minus gitignored paths: if `ds-bundle/` or `.ds-sync/` ever stop being gitignored, junk classes leak into the CSS (it grew 32 KB to 36 KB once).
- Grep tip: compiled selectors are escaped (`.sm\:py-12`); use `grep -F`.

## Known render warns
- none

## Re-sync risks
- `cfg.dtsPropsFor` duplicates `AvailabilityResponse`/`Slot`/`City` from `src/lib/api.ts` + `slots.ts`. Any envelope field change must be mirrored there by hand.
- `entry.ts` + `componentSrcMap` enumerate components by hand. A new component in `src/components/` isn't synced until it's added to both.
- `conventions.md` names the component classes from `src/index.css`. Rename one there and the header goes stale (re-validate against `_ds_bundle.css`).
- The Tailwind CLI version is pinned separately from the app's tailwindcss.
