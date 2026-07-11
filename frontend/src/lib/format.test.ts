import { describe, expect, it } from 'vitest'
import { formatSlotDate, formatSlotTime, timeAgo } from './format'

describe('formatSlotTime', () => {
  it('renders the wall-clock time written in the string (clinic-local), ignoring the machine timezone', () => {
    // Whatever timezone the test machine runs in, the clinic-local time is
    // the wall-clock part of the ISO string.
    expect(formatSlotTime('2026-07-10T14:30:00-07:00')).toBe('2:30 PM')
    expect(formatSlotTime('2026-07-10T09:05:00-07:00')).toBe('9:05 AM')
    expect(formatSlotTime('2026-07-10T14:30:00+02:00')).toBe('2:30 PM')
  })

  it('handles midnight and noon', () => {
    expect(formatSlotTime('2026-07-10T00:00:00-07:00')).toBe('12:00 AM')
    expect(formatSlotTime('2026-07-10T12:00:00-07:00')).toBe('12:00 PM')
  })
})

describe('formatSlotDate', () => {
  it('renders the clinic-local calendar date, ignoring the machine timezone', () => {
    // 2026-07-10 is a Friday. Late-evening Pacific times cross into the
    // next UTC day, which must not shift the displayed date.
    expect(formatSlotDate('2026-07-10T23:30:00-07:00')).toBe('Friday, July 10')
    expect(formatSlotDate('2026-07-11T00:15:00-07:00')).toBe('Saturday, July 11')
  })
})

describe('timeAgo', () => {
  const now = Date.parse('2026-07-10T12:00:00-07:00')

  it('says "just now" under a minute', () => {
    expect(timeAgo('2026-07-10T11:59:30-07:00', now)).toBe('just now')
  })

  it('reports whole minutes, singular and plural', () => {
    expect(timeAgo('2026-07-10T11:59:00-07:00', now)).toBe('1 minute ago')
    expect(timeAgo('2026-07-10T11:47:10-07:00', now)).toBe('12 minutes ago')
  })

  it('switches to hours after 60 minutes', () => {
    expect(timeAgo('2026-07-10T10:55:00-07:00', now)).toBe('1 hour ago')
    expect(timeAgo('2026-07-10T08:00:00-07:00', now)).toBe('4 hours ago')
  })

  it('switches to days after 24 hours', () => {
    expect(timeAgo('2026-07-08T09:00:00-07:00', now)).toBe('2 days ago')
  })
})
