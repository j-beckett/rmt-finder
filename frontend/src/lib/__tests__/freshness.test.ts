import { describe, expect, it } from 'vitest'
import { isStale, latestCheckFailed } from '../freshness'

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
