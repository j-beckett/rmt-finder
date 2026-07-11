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
