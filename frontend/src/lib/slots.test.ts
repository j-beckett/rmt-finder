import { describe, expect, it } from 'vitest'
import { sortSlots, type Slot } from './slots'

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
