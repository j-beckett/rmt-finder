import type { Slot } from './slots'

/** Envelope returned by GET /api/availability. */
export interface AvailabilityResponse {
  scraped_at: string | null
  latest_attempt_at: string | null
  clinics_attempted: number | null
  failed_clinics: string[]
  slots: Slot[]
}

// Same env-with-local-default pattern as backend/config.py; set
// VITE_API_BASE_URL (env var or .env file) to point elsewhere.
const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchAvailability(): Promise<AvailabilityResponse> {
  const response = await fetch(`${API_BASE_URL}/api/availability`)
  if (!response.ok) {
    throw new Error(`Availability request failed: ${response.status}`)
  }
  return response.json()
}
