# Implementation plan — Split App.tsx, add Studio Beckett footer

Status: built. Two steps, landed as one commit.

## Step 1: Split App.tsx into components (pure move)

`frontend/src/App.tsx` holds seven components. Logic already lives in
`src/lib/` with vitest coverage, so this is UI-layer only.

Files:

- `src/components/CityMenu.tsx`: `CityMenu` + `ChevronIcon` (not exported).
- `src/components/Availability.tsx`: `Availability`, plus
  `FALLBACK_TIMEZONE` and `FALLBACK_WINDOW_DAYS` (only it uses them).
- `src/components/MetaLine.tsx`: `MetaLine`.
- `src/components/SlotList.tsx`: `SlotGroups` + `SlotCard` (the Book-click
  `onClick`/`onAuxClick` tracking moves with it unchanged).
- `App.tsx` keeps `State`, the fetch/popstate/page-view effects,
  `chooseCity`, and the layout.

Rules:

- Code moves as-is: no renames, no markup or behaviour changes, no barrel
  files, no new hooks.
- Named exports for the moved components (`App` stays the default export).
- Imports use the `@/` alias; each file imports only what it uses.

No new tests: nothing new to assert, and the lib logic is already covered.
The proof is `npm test`, `npm run build` (tsc catches broken imports and
unused locals), `npm run lint`, and a side-by-side look in `npm run dev`.

## Step 2: Studio Beckett footer

Design is decided (not re-proposed here):

- One centred line, "A Studio Beckett project", all in Shadows Into Light,
  ~22px, `--color-forest`.
- Only "Studio Beckett" underlined: ~1.5px, forest at ~35% opacity.
- Whole line links to `https://studiobeckett.ca`, `rel="noopener"` only (no
  `noreferrer`, so the studio site sees referrals). No click tracking.
- Subtle top divider (forest ~18%), comfortable padding, fine at phone width.
- Added after review: "· Say hi", a `mailto:jen@studiobeckett.ca` link with
  the same underline. The studio site's contact section has no anchor to
  link to yet.

Files:

- `package.json`: add `@fontsource/shadows-into-light`.
- `src/index.css`: import it beside Fraunces/Inter; add the footer styles
  next to the other component classes.
- `src/components/Footer.tsx`: the footer.
- `App.tsx`: render `<Footer />` at the bottom of the page.

Validate: tests/build/lint pass; check desktop and 375px widths; confirm
no external font request in the network panel.
