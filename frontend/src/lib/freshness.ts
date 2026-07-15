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
