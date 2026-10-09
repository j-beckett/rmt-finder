import { describe, expect, it } from 'vitest'
import { cityFromSearch, searchWithCity } from '../city'

describe('cityFromSearch', () => {
  it('reads ?city= lowercased', () => {
    expect(cityFromSearch('?city=Langford')).toBe('langford')
  })

  it('is null when absent or blank, so the API picks its default', () => {
    expect(cityFromSearch('')).toBeNull()
    expect(cityFromSearch('?city=')).toBeNull()
    expect(cityFromSearch('?mock=empty')).toBeNull()
  })
})

describe('searchWithCity', () => {
  it('sets the city and keeps other params', () => {
    expect(searchWithCity('?mock=empty', 'langford')).toBe('?mock=empty&city=langford')
  })

  it('replaces an existing city', () => {
    expect(searchWithCity('?city=victoria', 'langford')).toBe('?city=langford')
  })
})
