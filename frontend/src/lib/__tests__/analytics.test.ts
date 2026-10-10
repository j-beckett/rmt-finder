import { describe, expect, it } from 'vitest'
import { bookClick, isTrackableClick, optedOut, pageView } from '../analytics'
import type { Slot } from '../slots'

function ready(city: string, city_name: string) {
  return { status: 'ready' as const, data: { city, city_name } }
}

describe('pageView', () => {
  it('counts the city the API served, even with no ?city= (default city)', () => {
    expect(pageView(ready('victoria', 'Victoria'), '')).toEqual({
      path: '/victoria',
      title: 'Victoria',
    })
  })

  it('counts each settled city on a switch or Back/Forward', () => {
    // App re-settles state per city; each settle is judged on its own.
    const views = [
      pageView(ready('victoria', 'Victoria'), '?city=victoria'),
      pageView(ready('langford', 'Langford & West Shore'), '?city=langford'),
      pageView(ready('victoria', 'Victoria'), '?city=victoria'),
    ]
    expect(views.map((v) => v?.path)).toEqual(['/victoria', '/langford', '/victoria'])
  })

  it('uses the served city key, not the URL spelling', () => {
    expect(pageView(ready('langford', 'Langford & West Shore'), '?city=LangFord')?.path).toBe(
      '/langford',
    )
  })

  it('keeps tracking params out of the path', () => {
    const search = '?city=victoria&fbclid=abc&utm_source=fb&utm_campaign=spring'
    expect(pageView(ready('victoria', 'Victoria'), search)?.path).toBe('/victoria')
  })

  it('groups an unknown city under one path, raw value in the title only', () => {
    const state = { status: 'error' as const, unknownCity: true }
    expect(pageView(state, '?city=Victorai&utm_source=fb')).toEqual({
      path: '/unknown-city',
      title: 'unknown city: Victorai',
    })
  })

  it('sends nothing on an API or network error', () => {
    const state = { status: 'error' as const, unknownCity: false }
    expect(pageView(state, '?city=victoria')).toBeNull()
  })

  it('sends nothing while loading', () => {
    expect(pageView({ status: 'loading' }, '?city=victoria')).toBeNull()
  })
})

function makeSlot(overrides: Partial<Slot>): Slot {
  return {
    clinic_name: 'Fern & Stone Massage',
    clinic_slug: 'fern-and-stone',
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

describe('bookClick', () => {
  it('is an event keyed by clinic slug, titled with the display name', () => {
    expect(bookClick(makeSlot({}))).toEqual({
      path: 'book/fern-and-stone',
      title: 'Fern & Stone Massage',
      event: true,
    })
  })

  it('sends nothing for a pre-slug slot rather than a junk key', () => {
    expect(bookClick(makeSlot({ clinic_slug: null }))).toBeNull()
  })
})

describe('isTrackableClick', () => {
  it('counts a primary click (tap, Ctrl/Cmd-click, keyboard Enter)', () => {
    expect(isTrackableClick({ type: 'click', button: 0 })).toBe(true)
  })

  it('counts a middle-click (open in new tab)', () => {
    expect(isTrackableClick({ type: 'auxclick', button: 1 })).toBe(true)
  })

  it('ignores a right-click; its menu may never open the link', () => {
    expect(isTrackableClick({ type: 'auxclick', button: 2 })).toBe(false)
    expect(isTrackableClick({ type: 'click', button: 2 })).toBe(false)
  })
})

function fakeStorage() {
  const items = new Map<string, string>()
  return {
    items,
    getItem: (key: string) => items.get(key) ?? null,
    setItem: (key: string, value: string) => void items.set(key, value),
    removeItem: (key: string) => void items.delete(key),
  }
}

describe('optedOut', () => {
  it('?notrack opts this browser out and remembers it', () => {
    const storage = fakeStorage()
    expect(optedOut('?notrack', () => storage)).toBe(true)
    expect(storage.items.size).toBe(1)
  })

  it('stays opted out on later visits without the param', () => {
    const storage = fakeStorage()
    optedOut('?notrack', () => storage)
    expect(optedOut('?city=victoria', () => storage)).toBe(true)
  })

  it('?notrack=off turns tracking back on for good', () => {
    const storage = fakeStorage()
    optedOut('?notrack', () => storage)
    expect(optedOut('?notrack=off', () => storage)).toBe(false)
    expect(optedOut('', () => storage)).toBe(false)
    expect(storage.items.size).toBe(0)
  })

  it('treats blocked or throwing storage as not opted out', () => {
    const blocked = () => {
      throw new DOMException('denied', 'SecurityError')
    }
    const throwing = { getItem: blocked, setItem: blocked, removeItem: blocked }
    for (const search of ['', '?notrack', '?notrack=off']) {
      expect(optedOut(search, blocked)).toBe(false)
      expect(optedOut(search, () => throwing)).toBe(false)
    }
  })
})
