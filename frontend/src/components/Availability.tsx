import { SCRAPE_INTERVAL_MINUTES, type AvailabilityResponse } from '@/lib/api'
import { isStale, latestCheckFailed, quietNote } from '@/lib/freshness'
import {
  formatPillLabel,
  formatSlotDate,
  spellOut,
  timeAgo,
  timeEmptyState,
  timeFilterSummary,
  todayInZone,
} from '@/lib/format'
import {
  addDays,
  filterSlotsByTime,
  filterSlotsByWindow,
  sortSlots,
  type SlotWindow,
  type TimeOfDay,
} from '@/lib/slots'
import { MetaLine } from '@/components/MetaLine'
import { SlotGroups } from '@/components/SlotList'
import { TimeFilter } from '@/components/TimeFilter'

// Fallback only for a stale/cached API that predates the envelope's timezone
// field; the current backend always sends it.
const FALLBACK_TIMEZONE = 'America/Vancouver'

// Matches the backend's LOOKAHEAD_DAYS default; used only if an old API
// omits window_days.
const FALLBACK_WINDOW_DAYS = 3

export function Availability({
  data,
  activeWindow,
  onWindowChange,
  activeTime,
  onTimeChange,
}: {
  data: AvailabilityResponse
  activeWindow: SlotWindow
  onWindowChange: (window: SlotWindow) => void
  activeTime: TimeOfDay | null
  onTimeChange: (time: TimeOfDay | null) => void
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
  // `?? null`: older APIs lack the field.
  const quiet = quietNote(
    data.scraped_at,
    data.quiet_hours ?? null,
    nowMs,
    SCRAPE_INTERVAL_MINUTES,
  )
  const stale =
    quiet === null && isStale(data.scraped_at, nowMs, SCRAPE_INTERVAL_MINUTES)
  const checkFailed = latestCheckFailed(data.scraped_at, data.latest_attempt_at)
  const all = sortSlots(data.slots)
  const dayShown = filterSlotsByWindow(all, activeWindow, today)
  const shown = filterSlotsByTime(dayShown, activeTime)
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
      <MetaLine
        data={data}
        nowMs={nowMs}
        latestCheckOk={!checkFailed}
        quietNote={quiet}
      />

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
        <div className="mt-5">
          <TimeFilter active={activeTime} onChange={onTimeChange} />
        </div>
        {activeTime && shown.length > 0 && (
          <div className="mt-3 flex items-center justify-between gap-4 max-w-md">
            <p className="text-sm text-moss">
              {timeFilterSummary(shown.length, activeTime)}
            </p>
            <button type="button" className="text-button" onClick={() => onTimeChange(null)}>
              Clear time
            </button>
          </div>
        )}
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
        ) : activeTime && dayShown.length > 0 ? (
          // The time filter emptied the list; the day itself has openings.
          <TimeEmpty
            {...timeEmptyState(activeTime, dayShown.length, activeWindow, today, windowLabel)}
            onClear={() => onTimeChange(null)}
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

function TimeEmpty({ title, body, onClear }: { title: string; body: string; onClear: () => void }) {
  return (
    <div className="empty-box">
      <h2 className="display text-2xl mb-2">{title}</h2>
      <p className="text-moss text-sm mb-5">{body}</p>
      <button type="button" className="filter-pill" aria-pressed="false" onClick={onClear}>
        Clear time
      </button>
    </div>
  )
}
