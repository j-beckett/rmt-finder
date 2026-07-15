import { useEffect, useState } from 'react'
import {
  fetchAvailability,
  SCRAPE_INTERVAL_MINUTES,
  type AvailabilityResponse,
} from '@/lib/api'
import { isStale, latestCheckFailed } from '@/lib/freshness'
import {
  formatDayLabel,
  formatShortDate,
  formatSlotTime,
  spellOut,
  timeAgo,
  todayInZone,
} from '@/lib/format'
import {
  filterSlotsByWindow,
  groupSlotsByDay,
  sortSlots,
  type Slot,
  type SlotWindow,
} from '@/lib/slots'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: AvailabilityResponse }

const WINDOWS = [
  { key: 'today', label: 'Today' },
  { key: 'tomorrow', label: 'Tomorrow' },
  { key: 'all', label: 'All' },
] as const satisfies readonly { key: SlotWindow; label: string }[]

// Fallback only for a stale/cached API that predates the envelope's timezone
// field; the current backend always sends it.
const FALLBACK_TIMEZONE = 'America/Vancouver'

function App() {
  const [state, setState] = useState<State>({ status: 'loading' })
  const [activeWindow, setActiveWindow] = useState<SlotWindow>('today')

  useEffect(() => {
    fetchAvailability()
      .then((data) => setState({ status: 'ready', data }))
      .catch((error: Error) => setState({ status: 'error', message: error.message }))
  }, [])

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
      <header>
        <h1 className="display text-4xl sm:text-5xl leading-none tracking-tight">
          Massage openings in Victoria
        </h1>
      </header>

      {state.status === 'loading' && (
        <p className="mt-6 text-moss">Loading availability…</p>
      )}

      {state.status === 'error' && (
        <div role="alert" className="empty-box mt-8">
          <h2 className="display text-2xl mb-2">Couldn't load availability</h2>
          <p className="text-moss text-sm">
            {state.message}. Check that the API is running, then refresh.
          </p>
        </div>
      )}

      {state.status === 'ready' && (
        <Availability
          data={state.data}
          activeWindow={activeWindow}
          onWindowChange={setActiveWindow}
        />
      )}
    </main>
  )
}

function Availability({
  data,
  activeWindow,
  onWindowChange,
}: {
  data: AvailabilityResponse
  activeWindow: SlotWindow
  onWindowChange: (window: SlotWindow) => void
}) {
  if (data.scraped_at === null) {
    return (
      <div className="empty-box mt-8">
        <h2 className="display text-2xl mb-2">No data yet</h2>
        <p className="text-moss text-sm">
          The first availability check hasn't completed. Check back in a few
          minutes.
        </p>
      </div>
    )
  }

  const nowMs = Date.now()
  const today = todayInZone(data.timezone || FALLBACK_TIMEZONE)
  const stale = isStale(data.scraped_at, nowMs, SCRAPE_INTERVAL_MINUTES)
  const checkFailed = latestCheckFailed(data.scraped_at, data.latest_attempt_at)
  const all = sortSlots(data.slots)
  const shown = filterSlotsByWindow(all, activeWindow, today)
  // e.g. "three days" — spelled out, from the envelope so it never hardcodes 3.
  // Degrades to "few days" if an old API omits window_days (never "undefined").
  const windowLabel =
    data.window_days > 0
      ? `${spellOut(data.window_days)} ${data.window_days === 1 ? 'day' : 'days'}`
      : 'few days'

  return (
    <>
      <MetaLine data={data} nowMs={nowMs} latestCheckOk={!checkFailed} />

      {stale && (
        <div role="alert" className="banner mt-5">
          <p className="display banner-title">
            This availability is out of date
          </p>
          <p className="banner-body">
            We haven't been able to refresh for a while — the last successful
            check was {timeAgo(data.scraped_at, nowMs)}, and these times may
            already be booked.
          </p>
        </div>
      )}

      {checkFailed && !stale && (
        <div role="status" className="notice mt-5">
          <span className="font-semibold">Our latest check didn't complete.</span>{' '}
          <span className="text-moss">
            Showing results from {timeAgo(data.scraped_at, nowMs)} — we'll keep
            trying.
          </span>
        </div>
      )}

      <div className="mt-6">
        <div role="group" aria-label="Time window" className="flex flex-wrap gap-2.5">
          {WINDOWS.map(({ key, label }) => (
            <button
              key={key}
              type="button"
              className="filter-pill"
              aria-pressed={key === activeWindow}
              onClick={() => onWindowChange(key)}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="mt-2.5 text-sm text-moss">
          The next {windowLabel} of openings
        </p>
      </div>

      <div className="mt-7">
        {shown.length > 0 ? (
          // Day badges only add information in the "all" view; for Today or
          // Tomorrow the badge would just repeat the active pill.
          <SlotGroups
            slots={shown}
            today={today}
            showDayBadges={activeWindow === 'all'}
          />
        ) : all.length > 0 ? (
          <div className="empty-box">
            <h2 className="display text-2xl mb-2">
              {activeWindow === 'today' ? 'Nothing left today' : 'Nothing tomorrow'}
            </h2>
            <p className="text-moss text-sm mb-5">
              Every clinic was checked — but there {all.length === 1 ? 'is' : 'are'}{' '}
              {all.length} {all.length === 1 ? 'opening' : 'openings'} in the next{' '}
              {windowLabel}.
            </p>
            <button
              type="button"
              className="filter-pill"
              aria-pressed="false"
              onClick={() => onWindowChange('all')}
            >
              Show all
            </button>
          </div>
        ) : (
          <div className="empty-box">
            <h2 className="display text-2xl mb-2">No openings right now</h2>
            <p className="text-moss text-sm">
              Every clinic was checked and nothing is bookable in the next{' '}
              {windowLabel}. New openings show up as soon as a clinic posts
              them — check back soon.
            </p>
          </div>
        )}
      </div>
    </>
  )
}

function MetaLine({
  data,
  nowMs,
  latestCheckOk,
}: {
  data: AvailabilityResponse
  nowMs: number
  latestCheckOk: boolean
}) {
  const failed = data.failed_clinics.length
  return (
    <div className="mt-3 text-sm text-moss">
      <p>
        Last updated {timeAgo(data.scraped_at!, nowMs)}
        {failed === 0 && latestCheckOk && ' · every clinic checked'}
      </p>
      {failed > 0 && (
        <p className="mt-0.5">
          {failed} of {data.clinics_attempted ?? '?'} clinics couldn't be
          checked — some openings may be missing.
        </p>
      )}
    </div>
  )
}

function SlotGroups({
  slots,
  today,
  showDayBadges,
}: {
  slots: Slot[]
  today: string
  showDayBadges: boolean
}) {
  return (
    <>
      {groupSlotsByDay(slots).map(({ date, slots: daySlots }) => (
        <section key={date} className="mb-7">
          {showDayBadges && (
            <span className="day-badge">{formatDayLabel(date, today)}</span>
          )}
          <ul className="mt-3.5 grid gap-4 list-none p-0">
            {daySlots.map((slot, i) => (
              <li key={i}>
                <SlotCard slot={slot} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  )
}

function SlotCard({ slot }: { slot: Slot }) {
  return (
    <a
      className="slot-card"
      href={slot.booking_url}
      target="_blank"
      rel="noopener noreferrer"
    >
      <span className="slot-time display">{formatSlotTime(slot.start_at)}</span>
      <span className="slot-date">{formatShortDate(slot.start_at)}</span>
      <span className="slot-clinic display">{slot.clinic_name}</span>
      <span className="slot-rmt">
        {slot.rmt_name} · {slot.duration_minutes} min
      </span>
      <span className="pill">Book ↗</span>
    </a>
  )
}

export default App
