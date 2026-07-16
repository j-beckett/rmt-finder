/** One bookable slot as returned by GET /api/availability. */
export interface Slot {
  clinic_name: string
  city: string
  platform: string
  rmt_name: string
  service_type: string
  treatment_name: string
  duration_minutes: number
  start_at: string
  booking_url: string
}

/** Slots ordered soonest-first by the absolute instant they start. */
export function sortSlots(slots: Slot[]): Slot[] {
  return [...slots].sort(
    (a, b) => Date.parse(a.start_at) - Date.parse(b.start_at),
  )
}

/** Clinic-local calendar date ("2026-07-13") of a slot's start time. */
function slotDate(slot: Slot): string {
  return slot.start_at.slice(0, 10)
}

/** "2026-07-13" + n days. Date.UTC handles month/year rollover. */
export function addDays(dateStr: string, n: number): string {
  const [year, month, day] = dateStr.split('-').map(Number)
  return new Date(Date.UTC(year, month - 1, day + n)).toISOString().slice(0, 10)
}

/**
 * A filter-pill window: a single day as an offset from today (0 = today,
 * 1 = tomorrow, …) or "all". Day pills are derived from the envelope's
 * window_days, so the UI grows with the collection window.
 */
export type SlotWindow = number | 'all'

/**
 * Slots visible in a given window, by clinic-local calendar date. "all" is
 * everything the envelope carries — so no collected slot is ever unreachable.
 * Calendar dates, not elapsed hours: at 11 PM, "Today" still means tonight's
 * remaining slots, not slots into tomorrow morning.
 */
export function filterSlotsByWindow(
  slots: Slot[],
  window: SlotWindow,
  today: string,
): Slot[] {
  if (window === 'all') return slots
  const target = addDays(today, window)
  return slots.filter((slot) => slotDate(slot) === target)
}

/** Group an already-sorted slot list by clinic-local date, preserving order. */
export function groupSlotsByDay(
  slots: Slot[],
): { date: string; slots: Slot[] }[] {
  const groups = new Map<string, Slot[]>()
  for (const slot of slots) {
    const date = slotDate(slot)
    const group = groups.get(date)
    if (group) group.push(slot)
    else groups.set(date, [slot])
  }
  return [...groups.entries()].map(([date, daySlots]) => ({
    date,
    slots: daySlots,
  }))
}
