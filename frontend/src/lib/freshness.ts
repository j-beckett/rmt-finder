import type { QuietWindow } from './api'
import { formatSlotTime } from './format'

/**
 * Freshness rules for the availability envelope. Pure functions — callers
 * pass the current time explicitly so the logic is testable.
 */

/** Served data is stale once it's older than 2x the scrape interval. */
export function isStale(
  scrapedAt: string,
  nowMs: number,
  intervalMinutes: number,
): boolean {
  return nowMs - Date.parse(scrapedAt) > 2 * intervalMinutes * 60_000
}

/**
 * True when the latest scrape attempt is newer than the served run — i.e.
 * the most recent check failed entirely and the API fell back to older data.
 */
export function latestCheckFailed(
  scrapedAt: string,
  latestAttemptAt: string | null,
): boolean {
  return (
    latestAttemptAt !== null &&
    Date.parse(latestAttemptAt) > Date.parse(scrapedAt)
  )
}

/**
 * True while checks are paused for quiet hours (overnight), so the page shows
 * a calm note instead of the "out of date" banner. Only when the data is from
 * around the start of the pause (a failure before it still shows as stale),
 * and through a grace period after it ends while the first check runs.
 */
export function isQuietPause(
  scrapedAt: string,
  quiet: QuietWindow | null,
  nowMs: number,
  intervalMinutes: number,
): boolean {
  if (quiet === null) return false
  const start = Date.parse(quiet.start)
  const allowedAge = 2 * intervalMinutes * 60_000
  // The data must be about as fresh as it was when checks paused; anything
  // older means checks were already failing, which the stale banner reports.
  const freshAtPause = Date.parse(scrapedAt) >= start - allowedAge
  // Grace after the window ends: the first morning check lands at the next
  // tick and takes a few minutes, so hold until it could have completed.
  const graceEnd = Date.parse(quiet.end) + allowedAge
  return freshAtPause && nowMs >= start && nowMs <= graceEnd
}

/**
 * The meta-line note shown during a quiet pause, or null. The resume time is
 * read from the window's own offset (like slot times), so a browser with stale
 * time zone data still shows the right hour.
 */
export function quietNote(
  scrapedAt: string,
  quiet: QuietWindow | null,
  nowMs: number,
  intervalMinutes: number,
): string | null {
  if (quiet === null || !isQuietPause(scrapedAt, quiet, nowMs, intervalMinutes)) {
    return null
  }
  // Past the end: the morning grace, while the first check of the day runs.
  if (nowMs >= Date.parse(quiet.end)) {
    return 'We pause checks overnight; the first one this morning is under way.'
  }
  return `We pause checks overnight and start again at ${formatSlotTime(quiet.end)}.`
}
