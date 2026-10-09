import { describe, expect, it } from 'vitest'
import { isQuietPause, isStale, latestCheckFailed, quietNote } from '../freshness'

const T0 = Date.parse('2026-07-13T10:00:00Z')
const minutes = (n: number) => n * 60_000

describe('isStale', () => {
  it('is fresh right after a scrape', () => {
    expect(isStale('2026-07-13T10:00:00Z', T0 + minutes(1), 15)).toBe(false)
  })

  it('is fresh at exactly 2x the scrape interval', () => {
    expect(isStale('2026-07-13T10:00:00Z', T0 + minutes(30), 15)).toBe(false)
  })

  it('is stale once older than 2x the scrape interval', () => {
    expect(isStale('2026-07-13T10:00:00Z', T0 + minutes(31), 15)).toBe(true)
  })

  it('scales the threshold with the interval', () => {
    expect(isStale('2026-07-13T10:00:00Z', T0 + minutes(31), 30)).toBe(false)
    expect(isStale('2026-07-13T10:00:00Z', T0 + minutes(61), 30)).toBe(true)
  })
})

describe('latestCheckFailed', () => {
  it('is false when the served run is the latest attempt', () => {
    expect(latestCheckFailed('2026-07-13T10:00:00Z', '2026-07-13T10:00:00Z')).toBe(false)
  })

  it('is false when the envelope has no latest attempt', () => {
    expect(latestCheckFailed('2026-07-13T10:00:00Z', null)).toBe(false)
  })

  it('is true when the latest attempt is newer than the served run', () => {
    expect(latestCheckFailed('2026-07-13T10:00:00Z', '2026-07-13T10:15:00Z')).toBe(true)
  })
})

describe('isQuietPause', () => {
  // Last night's window, as the API sends it (Vancouver, UTC-7).
  const QUIET = { start: '2026-10-08T23:00:00-07:00', end: '2026-10-09T06:00:00-07:00' }
  const at = (iso: string) => Date.parse(iso)

  it('is false when quiet hours are off', () => {
    expect(
      isQuietPause('2026-10-08T22:50:00-07:00', null, at('2026-10-09T03:00:00-07:00'), 15),
    ).toBe(false)
  })

  it('is true overnight when the data is from just before the window', () => {
    // Last scrape 22:50, now 03:00: four hours old, but nothing failed.
    expect(
      isQuietPause('2026-10-08T22:50:00-07:00', QUIET, at('2026-10-09T03:00:00-07:00'), 15),
    ).toBe(true)
  })

  it('is false when the data predates the window: a real failure stays visible', () => {
    // Last good scrape 21:00, so checks were already failing before 23:00.
    expect(
      isQuietPause('2026-10-08T21:00:00-07:00', QUIET, at('2026-10-09T03:00:00-07:00'), 15),
    ).toBe(false)
  })

  it('holds through the morning grace while the first check runs', () => {
    // The 06:00 tick scrapes for a few minutes; no "out of date" flash.
    const lastNight = '2026-10-08T22:50:00-07:00'
    expect(isQuietPause(lastNight, QUIET, at('2026-10-09T06:00:00-07:00'), 15)).toBe(true)
    expect(isQuietPause(lastNight, QUIET, at('2026-10-09T06:30:00-07:00'), 15)).toBe(true)
    expect(isQuietPause(lastNight, QUIET, at('2026-10-09T06:31:00-07:00'), 15)).toBe(false)
  })
})

describe('quietNote', () => {
  const QUIET = { start: '2026-10-08T23:00:00-07:00', end: '2026-10-09T06:00:00-07:00' }

  it('says when checks start again, in clinic-local time', () => {
    expect(
      quietNote('2026-10-08T22:50:00-07:00', QUIET, Date.parse('2026-10-09T03:00:00-07:00'), 15),
    ).toBe('We pause checks overnight and start again at 6:00 AM.')
  })

  it('is null outside a quiet pause', () => {
    expect(
      quietNote('2026-10-09T11:50:00-07:00', QUIET, Date.parse('2026-10-09T12:00:00-07:00'), 15),
    ).toBeNull()
  })

  it('says the first morning check is under way once the window has ended', () => {
    expect(
      quietNote('2026-10-08T22:50:00-07:00', QUIET, Date.parse('2026-10-09T06:10:00-07:00'), 15),
    ).toBe('We pause checks overnight; the first one this morning is under way.')
  })
})
