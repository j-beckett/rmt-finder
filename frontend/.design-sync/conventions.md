# RMT Finder: how to build with it

A retro warm/wellness look: cream page, deep forest ink, chartreuse (lime) accent, a chunky soft serif for display text, and outlined "sticker" surfaces with hard offset shadows. These are the real components from the rmt-finder app (massage-appointment availability).

## Setup

No provider or wrapper is needed. Link `styles.css` once. It carries the Tailwind v4 utilities, the theme tokens and the fonts, and it sets the cream page background and forest text color on `html`. Put page content in the app's column: `<main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">`.

## Styling idiom: Tailwind utilities + a few component classes

Use Tailwind utility classes with the theme names below. Don't use raw hex values, and don't invent new class names.

| Family | Names |
|---|---|
| Colors (`bg-`/`text-`/`border-`) | `cream` (page), `card` (surface), `forest` (ink, borders, shadows), `panel` (dark banner), `moss` (muted text), `lime` (accent), `lime-bright` (accent on dark) |
| Fonts | `font-sans` (Inter, body), `font-display` (Fraunces), `font-hand` (Shadows Into Light: credits only) |
| CSS vars | `var(--color-forest)`, `var(--color-lime)`, … `var(--font-display)` |

Component classes (defined in `_ds_bundle.css`; reuse them for anything new that should match):

- `display`: Fraunces at weight 900 with soft corners. Use it on every heading (`<h1 className="display text-4xl sm:text-5xl leading-none tracking-tight">`). Prefer it over plain `font-display`.
- `pill`: lime uppercase sticker badge (the "Book ↗" chip).
- `filter-pill`: outlined uppercase toggle button. Set `aria-pressed="true"` to switch it to the lime active state.
- `day-badge`: small outlined uppercase separator label.
- `slot-card`: the outlined card with a 4px hard shadow. Use `slot-time`, `slot-date`, `slot-clinic` and `slot-rmt` for its parts.
- `banner` with `banner-title`/`banner-body`: dark forest alert panel with a lime headline.
- `notice`: calm outlined info box. `empty-box`: dashed, centered empty state.

Accent rule: lime marks only *active* or *book* things. Supporting text is `text-moss text-sm`.

## Components

- `Availability`: the full results view (meta line, staleness banner/notice, day filter pills, slot list, empty states). It takes the whole API envelope; you own `activeWindow` state (`0` = today, `1` = tomorrow, …, `"all"`).
- `SlotGroups`: day-grouped list of bookable slot cards.
- `SlotCard`: one bookable opening (time, clinic, RMT · duration, Book pill). The whole card links to `slot.booking_url`. Use it for single highlights like "Next available"; use `SlotGroups` for lists.
- `MetaLine`: the "Last updated N minutes ago · all clinics checked" line.
- `CityMenu`: pill button with a listbox dropdown for switching cities.
- `Footer`: the Studio Beckett credit.

Exact props are in `components/general/<Name>/<Name>.d.ts`, with examples in `<Name>.prompt.md`. Slot `start_at` is clinic-local ISO with an offset (`"2026-07-17T14:30:00-07:00"`). `scraped_at` is UTC ISO. A `scraped_at` of null renders "No data yet".

## Example

```jsx
const { SlotGroups } = window.RmtFinder;
const slot = {
  clinic_name: 'Fern & Stone Massage', clinic_slug: 'fern-stone', city: 'victoria',
  platform: 'jane', rmt_name: 'Priya Natarajan', service_type: 'massage',
  treatment_name: '60 Minute Massage', duration_minutes: 60,
  start_at: '2026-07-17T10:30:00-07:00', booking_url: 'https://example.janeapp.com/',
};

<main className="mx-auto max-w-3xl px-4 py-8">
  <h1 className="display text-4xl leading-none tracking-tight">Massage openings in Victoria</h1>
  <p className="mt-3 text-moss">Showing bookable RMT appointments across 14 clinics.</p>
  <div className="mt-8">
    <SlotGroups slots={[slot]} today="2026-07-17" showDayBadges />
  </div>
</main>
```
