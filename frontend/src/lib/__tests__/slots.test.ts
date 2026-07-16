import { describe, expect, it } from 'vitest'
import {
  addDays,
  filterSlotsByWindow,
  groupSlotsByDay,
  sortSlots,
  type Slot,
} from '../slots'

function makeSlot(overrides: Partial<Slot>): Slot {
  return {
    clinic_name: 'Fern & Stone Massage',
    city: 'Victoria',
    platform: 'jane',
    rmt_name: 'Alex Chen',
    service_type: 'massage_therapy',
    treatment_name: '60 min massage',
    duration_minutes: 60,
    start_at: '2026-07-10T09:00:00-07:00',
    booking_url: 'https://example.janeapp.com/#/book',
    ...overrides,
  }
}

describe('sortSlots', () => {
  it('orders slots soonest-first', () => {
    const later = makeSlot({ start_at: '2026-07-10T15:30:00-07:00' })
    const soonest = makeSlot({ start_at: '2026-07-10T09:15:00-07:00' })
    const middle = makeSlot({ start_at: '2026-07-10T11:00:00-07:00' })

    const sorted = sortSlots([later, soonest, middle])

    expect(sorted.map((s) => s.start_at)).toEqual([
      '2026-07-10T09:15:00-07:00',
      '2026-07-10T11:00:00-07:00',
      '2026-07-10T15:30:00-07:00',
    ])
  })

  it('compares by absolute instant, not wall-clock string, across offsets', () => {
    // 10:00 at -04:00 is 14:00 UTC; 09:00 at -07:00 is 16:00 UTC.
    // Wall-clock (and string) order would wrongly put 09:00 first.
    const earlierInstant = makeSlot({ start_at: '2026-07-10T10:00:00-04:00' })
    const laterInstant = makeSlot({ start_at: '2026-07-10T09:00:00-07:00' })

    const sorted = sortSlots([laterInstant, earlierInstant])

    expect(sorted.map((s) => s.start_at)).toEqual([
      '2026-07-10T10:00:00-04:00',
      '2026-07-10T09:00:00-07:00',
    ])
  })
})

describe('addDays', () => {
  it('adds within a month', () => {
    expect(addDays('2026-07-13', 2)).toBe('2026-07-15')
  })

  it('rolls over month and year boundaries', () => {
    expect(addDays('2026-07-31', 1)).toBe('2026-08-01')
    expect(addDays('2026-12-31', 1)).toBe('2027-01-01')
  })
})

describe('filterSlotsByWindow', () => {
  const today = makeSlot({ start_at: '2026-07-13T14:00:00-07:00' })
  const tomorrow = makeSlot({ start_at: '2026-07-14T09:00:00-07:00' })
  const dayAfter = makeSlot({ start_at: '2026-07-15T11:00:00-07:00' })
  const all = [today, tomorrow, dayAfter]

  it('keeps only today for day offset 0', () => {
    expect(filterSlotsByWindow(all, 0, '2026-07-13')).toEqual([today])
  })

  it('keeps only tomorrow for day offset 1 (not today)', () => {
    expect(filterSlotsByWindow(all, 1, '2026-07-13')).toEqual([tomorrow])
  })

  it('reaches the third day directly with offset 2', () => {
    expect(filterSlotsByWindow(all, 2, '2026-07-13')).toEqual([dayAfter])
  })

  it('keeps everything for the "all" window, including the far day', () => {
    expect(filterSlotsByWindow(all, 'all', '2026-07-13')).toEqual(all)
  })

  it('filters by clinic-local calendar date, not elapsed hours', () => {
    // 11:30 PM today is under 1h away but still "today"; 9 AM tomorrow is
    // ~10h away but excluded from the today window.
    const lateTonight = makeSlot({ start_at: '2026-07-13T23:30:00-07:00' })
    expect(
      filterSlotsByWindow([lateTonight, tomorrow], 0, '2026-07-13'),
    ).toEqual([lateTonight])
  })

  it('crosses a month boundary for the tomorrow window', () => {
    const augFirst = makeSlot({ start_at: '2026-08-01T09:00:00-07:00' })
    expect(filterSlotsByWindow([augFirst], 1, '2026-07-31')).toEqual([augFirst])
  })
})

describe('groupSlotsByDay', () => {
  it('groups a sorted list by clinic-local date, preserving order', () => {
    const a = makeSlot({ start_at: '2026-07-13T14:00:00-07:00' })
    const b = makeSlot({ start_at: '2026-07-13T16:00:00-07:00' })
    const c = makeSlot({ start_at: '2026-07-14T09:00:00-07:00' })

    expect(groupSlotsByDay([a, b, c])).toEqual([
      { date: '2026-07-13', slots: [a, b] },
      { date: '2026-07-14', slots: [c] },
    ])
  })

  it('returns no groups for no slots', () => {
    expect(groupSlotsByDay([])).toEqual([])
  })
})
