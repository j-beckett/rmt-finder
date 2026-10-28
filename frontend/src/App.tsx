import { useEffect, useState } from 'react'
import {
  fetchAvailability,
  fetchCities,
  SCRAPE_INTERVAL_MINUTES,
  type AvailabilityResponse,
  type City,
  UnknownCityError,
} from '@/lib/api'
import { pageView } from '@/lib/analytics'
import { cityFromSearch, searchWithCity } from '@/lib/city'
import { send } from '@/lib/track'
import type { SlotWindow, TimeOfDay } from '@/lib/slots'
import { Availability } from '@/components/Availability'
import { CityMenu } from '@/components/CityMenu'
import { Footer } from '@/components/Footer'
import logoIcon from '@/assets/logo-icon.png'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string; unknownCity: boolean }
  | { status: 'ready'; data: AvailabilityResponse }

function App() {
  // The URL is the source of truth, so a shared ?city= link preloads that city.
  const [city, setCity] = useState(() => cityFromSearch(window.location.search))
  const [cities, setCities] = useState<City[]>([])
  const [state, setState] = useState<State>({ status: 'loading' })
  const [activeWindow, setActiveWindow] = useState<SlotWindow>(0)
  const [activeTime, setActiveTime] = useState<TimeOfDay | null>(null)

  useEffect(() => {
    // Ignore a slow response for a city the user has already switched away from.
    let current = true
    setState({ status: 'loading' })
    fetchAvailability(city)
      .then((data) => current && setState({ status: 'ready', data }))
      .catch(
        (error: Error) =>
          current &&
          setState({
            status: 'error',
            message: error.message,
            unknownCity: error instanceof UnknownCityError,
          }),
      )
    return () => {
      current = false
    }
  }, [city])

  useEffect(() => {
    // State changes only when a fetch starts or settles, so this is one view per city shown.
    send(pageView(state, window.location.search))
  }, [state])

  useEffect(() => {
    // Without the list the title just shows the served city, so failure is quiet.
    fetchCities().then(setCities).catch(() => {})
  }, [])

  useEffect(() => {
    const onPopState = () => setCity(cityFromSearch(window.location.search))
    window.addEventListener('popstate', onPopState)
    return () => window.removeEventListener('popstate', onPopState)
  }, [])

  function chooseCity(slug: string) {
    // pushState, not a reload: the URL stays shareable and Back returns here.
    window.history.pushState(null, '', searchWithCity(window.location.search, slug))
    setCity(slug)
  }

  const servedCity = state.status === 'ready' ? state.data.city : city
  const cityName =
    state.status === 'ready'
      ? state.data.city_name
      : cities.find((c) => c.slug === city)?.name

  return (
    <>
      <main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
        <header>
          <div className="flex items-center gap-3 mb-6 sm:mb-7">
            <img src={logoIcon} alt="" className="h-10 w-auto" />
            <span className="display text-2xl leading-none">rmt finder</span>
          </div>
          <h1 className="display text-4xl sm:text-5xl leading-none tracking-tight">
            Massage openings{cityName && ` in ${cityName}`}
          </h1>
          {state.status === 'ready' && (
            <p className="mt-3 text-moss">
              Showing bookable RMT appointments
              {state.data.clinics_total > 0 &&
                ` across ${state.data.clinics_total} clinics`}
              , rechecked every {SCRAPE_INTERVAL_MINUTES} minutes
              {state.data.quiet_hours && ', except overnight'}.
            </p>
          )}
          {cities.length > 1 && (
            <CityMenu cities={cities} value={servedCity} onChange={chooseCity} />
          )}
        </header>

        {state.status === 'loading' && (
          <p className="mt-6 text-moss">Loading availability…</p>
        )}

        {state.status === 'error' && (
          <div role="alert" className="empty-box mt-8">
            <h2 className="display text-2xl mb-2">Couldn't load availability</h2>
            <p className="text-moss text-sm">
              {state.unknownCity
                ? `${state.message}. Choose a city above.`
                : `${state.message}. Check that the API is running, then refresh.`}
            </p>
          </div>
        )}

        {state.status === 'ready' && (
          <Availability
            data={state.data}
            activeWindow={activeWindow}
            onWindowChange={setActiveWindow}
            activeTime={activeTime}
            onTimeChange={setActiveTime}
          />
        )}
      </main>
      <Footer />
    </>
  )
}

export default App
