import { useEffect, useState } from 'react'
import {
  fetchAvailability,
  SCRAPE_INTERVAL_MINUTES,
  type AvailabilityResponse,
} from '@/lib/api'
import { isStale, latestCheckFailed } from '@/lib/freshness'
import {
  formatDayLabel,
  formatPillLabel,
  formatShortDate,
  formatSlotDate,
  formatSlotTime,
  spellOut,
  timeAgo,
  todayInZone,
} from '@/lib/format'
import {
  addDays,
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

// Fallback only for a stale/cached API that predates the envelope's timezone
// field; the current backend always sends it.
const FALLBACK_TIMEZONE = 'America/Vancouver'

// Matches the backend's LOOKAHEAD_DAYS default; used only if an old API
// omits window_days.
const FALLBACK_WINDOW_DAYS = 3

function App() {
  const [state, setState] = useState<State>({ status: 'loading' })
  const [activeWindow, setActiveWindow] = useState<SlotWindow>(0)

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
        {state.status === 'ready' && (
          <p className="mt-3 text-moss">
            Showing bookable RMT appointments
            {state.data.clinics_total > 0 &&
              ` across ${state.data.clinics_total} clinics`}
            , rechecked every {SCRAPE_INTERVAL_MINUTES} minutes.
          </p>
        )}
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
  const windowDays = data.window_days > 0 ? data.window_days : FALLBACK_WINDOW_DAYS
  // One pill per collected day plus "All", so every day is one tap away and
  // the pill row grows with the envelope's window. Weekday pills carry a
  // short form ("Fri 17") so the row fits one line on phones.
  const pills: { key: SlotWindow; label: string; shortLabel: string }[] = [
    ...Array.from({ length: windowDays }, (_, n) => {
      const date = addDays(today, n)
      return {
        key: n as SlotWindow,
        label: formatPillLabel(date, today),
        shortLabel: formatPillLabel(date, today, 'short'),
      }
    }),
    { key: 'all' as SlotWindow, label: 'All', shortLabel: 'All' },
  ]
  // e.g. "three days" — spelled out, from the envelope so it never hardcodes 3.
  const windowLabel = `${spellOut(windowDays)} ${windowDays === 1 ? 'day' : 'days'}`
  // Under the pills: the active day's full date. "All" gets no caption — its
  // day badges already say where you are.
  const caption =
    activeWindow === 'all' ? null : formatSlotDate(addDays(today, activeWindow))

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

      <div className="mt-8">
        <div role="group" aria-label="Time window" className="flex flex-wrap gap-2.5">
          {pills.map(({ key, label, shortLabel }) => (
            <button
              key={key}
              type="button"
              className="filter-pill"
              aria-pressed={key === activeWindow}
              onClick={() => onWindowChange(key)}
            >
              <span className="sm:hidden">{shortLabel}</span>
              <span className="hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>
        {caption && <p className="mt-4 text-sm text-moss">{caption}</p>}
      </div>

      <div className="mt-9">
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
              {activeWindow === 0
                ? 'Nothing left today'
                : activeWindow === 1
                  ? 'Nothing tomorrow'
                  : // "Nothing on Friday" — weekday from "Friday, July 17".
                    `Nothing on ${formatSlotDate(addDays(today, activeWindow as number)).split(',')[0]}`}
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
        {failed === 0 && latestCheckOk && ' · all clinics checked'}
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
