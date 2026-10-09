/** The ?city= param, lowercased; null lets the API use its default city. */
export function cityFromSearch(search: string): string | null {
  const city = new URLSearchParams(search).get('city')
  return city ? city.toLowerCase() : null
}

/** `search` with ?city= set, keeping any other params (e.g. ?mock=). */
export function searchWithCity(search: string, city: string): string {
  const params = new URLSearchParams(search)
  params.set('city', city)
  return `?${params}`
}
