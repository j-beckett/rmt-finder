import type { AvailabilityResponse } from './api'
import type { Slot } from './slots'

/**
 * Dev-only envelope fixtures for reviewing UI states by eye, served when the
 * page is loaded with ?mock=<scenario> (see api.ts). Timestamps are relative
 * to "now" so the freshness math behaves the same whenever they're viewed.
 *
 * Scenarios: fresh · stale · partial · failed · empty · empty-today · error
 *            quiet · quiet-morning · quiet-failed
 */

const HOUR = 3_600_000
const MINUTE = 60_000

/** UTC ISO timestamp `msAgo` in the past, like the envelope's scraped_at. */
function utcAgo(msAgo: number): string {
  return new Date(Date.now() - msAgo).toISOString()
}

/**
 * Clinic-local ISO start time `msFromNow` ahead, pinned to Victoria's summer
 * offset (-07:00) like real Jane slot times.
 */
function localFromNow(msFromNow: number): string {
  const wall = new Date(Date.now() + msFromNow - 7 * HOUR)
  return wall.toISOString().slice(0, 19) + '-07:00'
}

/** The next 06:00 Victoria wall-clock time (-07:00), as the API sends it. */
function nextSixAm(): string {
  const wall = new Date(Date.now() - 7 * HOUR)
  const six = new Date(wall)
  six.setUTCHours(6, 0, 0, 0)
  if (six <= wall) six.setUTCDate(six.getUTCDate() + 1)
  return six.toISOString().slice(0, 19) + '-07:00'
}

function slot(
  msFromNow: number,
  clinic: string,
  rmt: string,
  minutes: number,
): Slot {
  return {
    clinic_name: clinic,
    city: 'Victoria',
    platform: 'jane',
    rmt_name: rmt,
    service_type: 'massage_therapy',
    treatment_name: `${minutes} min massage`,
    duration_minutes: minutes,
    start_at: localFromNow(msFromNow),
    booking_url: 'https://example.janeapp.com/#/book',
  }
}

function threeDaysOfSlots(): Slot[] {
  return [
    slot(2 * HOUR, 'Equilibrium Massage Therapy', 'Alex Chen', 60),
    slot(4.5 * HOUR, 'Tall Tree Health', 'Priya Sandhu', 45),
    slot(26 * HOUR, 'Victoria Centre Acupuncture & Massage', 'Mei Wong', 60),
    slot(29 * HOUR, 'Moss Healthcare', 'Jordan Lee', 45),
    slot(31 * HOUR, 'Equilibrium Massage Therapy', 'Sam Rivera', 90),
    slot(50 * HOUR, 'Tall Tree Health', 'Priya Sandhu', 60),
  ]
}

function envelope(overrides: Partial<AvailabilityResponse>): AvailabilityResponse {
  return {
    scraped_at: utcAgo(4 * MINUTE),
    latest_attempt_at: utcAgo(4 * MINUTE),
    clinics_attempted: 23,
    failed_clinics: [],
    window_days: 3,
    city: 'victoria',
    city_name: 'Victoria',
    timezone: 'America/Vancouver',
    clinics_total: 23,
    quiet_hours: null,
    slots: threeDaysOfSlots(),
    ...overrides,
  }
}

export function mockEnvelope(scenario: string): AvailabilityResponse {
  switch (scenario) {
    case 'fresh':
      return envelope({})
    case 'stale':
      return envelope({
        scraped_at: utcAgo(75 * MINUTE),
        latest_attempt_at: utcAgo(75 * MINUTE),
      })
    case 'partial':
      return envelope({
        failed_clinics: ['Fern & Stone Massage', 'Harbourview Wellness'],
      })
    case 'failed':
      // Served run is 20 min old (not yet stale); a newer attempt got nothing.
      return envelope({
        scraped_at: utcAgo(20 * MINUTE),
        latest_attempt_at: utcAgo(3 * MINUTE),
      })
    case 'empty':
      return envelope({ slots: [] })
    case 'empty-today':
      return envelope({ slots: threeDaysOfSlots().slice(2) })
    case 'quiet':
      // Paused 4h ago; stretched to end at a real 06:00 so the note reads true.
      return envelope({
        scraped_at: utcAgo(4 * HOUR + 10 * MINUTE),
        latest_attempt_at: utcAgo(4 * HOUR + 10 * MINUTE),
        quiet_hours: { start: localFromNow(-4 * HOUR), end: nextSixAm() },
      })
    case 'quiet-morning':
      // 10 minutes after the window; first check not landed yet.
      return envelope({
        scraped_at: utcAgo(7 * HOUR + 20 * MINUTE),
        latest_attempt_at: utcAgo(7 * HOUR + 20 * MINUTE),
        quiet_hours: {
          start: localFromNow(-7 * HOUR - 10 * MINUTE),
          end: localFromNow(-10 * MINUTE),
        },
      })
    case 'quiet-failed':
      // Checks already failing before the pause: still stale.
      return envelope({
        scraped_at: utcAgo(6 * HOUR),
        latest_attempt_at: utcAgo(4 * HOUR + 10 * MINUTE),
        quiet_hours: { start: localFromNow(-4 * HOUR), end: localFromNow(3 * HOUR) },
      })
    case 'error':
      throw new Error('mock: simulated network failure')
    default:
      throw new Error(`unknown mock scenario: ${scenario}`)
  }
}
