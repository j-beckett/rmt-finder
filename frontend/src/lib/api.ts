import type { Slot } from './slots'

/** Envelope returned by GET /api/availability. */
export interface AvailabilityResponse {
  scraped_at: string | null
  latest_attempt_at: string | null
  clinics_attempted: number | null
  failed_clinics: string[]
  /** Whole calendar days the scrape covers (drives the "All" window + copy). */
  window_days: number
  /** IANA timezone of the served city, for computing its local "today". */
  timezone: string
  /** Clinics on the scrape roster (from clinics.py), for the about line. */
  clinics_total: number
  slots: Slot[]
}

// Same env-with-local-default pattern as backend/config.py; set
// VITE_API_BASE_URL (env var or .env file) to point elsewhere.
const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

// Mirrors the backend's SCRAPE_INTERVAL_MINUTES so the staleness threshold
// (2x interval) matches how often data actually refreshes.
export const SCRAPE_INTERVAL_MINUTES: number = Number(
  import.meta.env.VITE_SCRAPE_INTERVAL_MINUTES ?? '15',
)

export async function fetchAvailability(): Promise<AvailabilityResponse> {
  // Dev-only: ?mock=<scenario> serves a crafted envelope so each UI state
  // can be reviewed by eye (see mockEnvelopes.ts for scenarios). The dynamic
  // import keeps the fixtures out of production builds.
  if (import.meta.env.DEV) {
    const scenario = new URLSearchParams(window.location.search).get('mock')
    if (scenario) {
      const { mockEnvelope } = await import('./mockEnvelopes')
      return mockEnvelope(scenario)
    }
  }

  const response = await fetch(`${API_BASE_URL}/api/availability`)
  if (!response.ok) {
    throw new Error(`Availability request failed: ${response.status}`)
  }
  return response.json()
}
