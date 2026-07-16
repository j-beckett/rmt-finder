import { describe, expect, it } from 'vitest'
import {
  formatDayLabel,
  formatPillLabel,
  formatShortDate,
  formatSlotDate,
  formatSlotTime,
  spellOut,
  timeAgo,
  todayInZone,
} from '../format'

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

describe('todayInZone', () => {
  it('uses the given timezone, not the machine timezone', () => {
    // 2026-07-14 05:00 UTC is still 2026-07-13 (10 PM PDT) in Vancouver.
    const instant = new Date('2026-07-14T05:00:00Z')
    expect(todayInZone('America/Vancouver', instant)).toBe('2026-07-13')
  })

  it('rolls to the next day once the zone passes midnight', () => {
    // 2026-07-14 08:00 UTC is 2026-07-14 (1 AM PDT) in Vancouver.
    const instant = new Date('2026-07-14T08:00:00Z')
    expect(todayInZone('America/Vancouver', instant)).toBe('2026-07-14')
  })
})

describe('spellOut', () => {
  it('spells small whole numbers as words', () => {
    expect(spellOut(1)).toBe('one')
    expect(spellOut(3)).toBe('three')
    expect(spellOut(10)).toBe('ten')
  })

  it('falls back to digits past ten', () => {
    expect(spellOut(14)).toBe('14')
  })
})

describe('formatShortDate', () => {
  it('renders the clinic-local month and day without weekday', () => {
    expect(formatShortDate('2026-07-10T23:30:00-07:00')).toBe('July 10')
  })
})

describe('formatPillLabel', () => {
  it('labels today and tomorrow by name', () => {
    expect(formatPillLabel('2026-07-13', '2026-07-13')).toBe('Today')
    expect(formatPillLabel('2026-07-14', '2026-07-13')).toBe('Tomorrow')
  })

  it('labels days beyond tomorrow with full weekday + day', () => {
    expect(formatPillLabel('2026-07-15', '2026-07-13')).toBe('Wednesday 15')
  })
})

describe('formatDayLabel', () => {
  it('labels today and tomorrow by name', () => {
    expect(formatDayLabel('2026-07-13', '2026-07-13')).toBe('Today')
    expect(formatDayLabel('2026-07-14', '2026-07-13')).toBe('Tomorrow')
  })

  it('falls back to the full date beyond tomorrow', () => {
    expect(formatDayLabel('2026-07-15', '2026-07-13')).toBe(
      'Wednesday, July 15',
    )
  })

  it('crosses month boundaries when naming tomorrow', () => {
    expect(formatDayLabel('2026-08-01', '2026-07-31')).toBe('Tomorrow')
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
