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

/** True during an overnight pause (plus morning grace), so no stale banner. */
export function isQuietPause(
  scrapedAt: string,
  quiet: QuietWindow | null,
  nowMs: number,
  intervalMinutes: number,
): boolean {
  if (quiet === null) return false
  const start = Date.parse(quiet.start)
  const allowedAge = 2 * intervalMinutes * 60_000
  // Older data means checks were failing before the pause: let it show stale.
  const freshAtPause = Date.parse(scrapedAt) >= start - allowedAge
  // Grace while the first morning check runs.
  const graceEnd = Date.parse(quiet.end) + allowedAge
  return freshAtPause && nowMs >= start && nowMs <= graceEnd
}

/** Meta-line note during a quiet pause, or null. */
export function quietNote(
  scrapedAt: string,
  quiet: QuietWindow | null,
  nowMs: number,
  intervalMinutes: number,
): string | null {
  if (quiet === null || !isQuietPause(scrapedAt, quiet, nowMs, intervalMinutes)) {
    return null
  }
  if (nowMs >= Date.parse(quiet.end)) {
    return 'We pause checks overnight; the first one this morning is under way.'
  }
  return `We pause checks overnight and start again at ${formatSlotTime(quiet.end)}.`
}
