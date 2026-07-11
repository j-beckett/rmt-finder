/**
 * Clinic-local display helpers.
 *
 * Slot start times arrive as ISO strings whose wall-clock part is already
 * the clinic's local time (offset included, e.g. "2026-07-10T14:30:00-07:00").
 * We read that wall-clock part directly instead of going through Date, which
 * would silently convert to the machine's timezone.
 */

/** "2026-07-10T14:30:00-07:00" → "2:30 PM" */
export function formatSlotTime(startAt: string): string {
  const [hourStr, minuteStr] = startAt.slice(11, 16).split(':')
  const hour24 = Number(hourStr)
  const hour12 = hour24 % 12 === 0 ? 12 : hour24 % 12
  const meridiem = hour24 < 12 ? 'AM' : 'PM'
  return `${hour12}:${minuteStr} ${meridiem}`
}

/** "2026-07-10T23:30:00-07:00" → "Friday, July 10" */
export function formatSlotDate(startAt: string): string {
  const [year, month, day] = startAt.slice(0, 10).split('-').map(Number)
  // Date.UTC keeps the clinic-local calendar date intact; formatting that
  // instant in UTC can never roll it into a neighbouring day.
  const date = new Date(Date.UTC(year, month - 1, day))
  return date.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

/** "how long ago" line for the served run, e.g. "12 minutes ago". */
export function timeAgo(iso: string, nowMs: number): string {
  const elapsedMinutes = Math.floor((nowMs - Date.parse(iso)) / 60_000)
  if (elapsedMinutes < 1) return 'just now'
  if (elapsedMinutes < 60) return plural(elapsedMinutes, 'minute')
  const hours = Math.floor(elapsedMinutes / 60)
  if (hours < 24) return plural(hours, 'hour')
  return plural(Math.floor(hours / 24), 'day')
}

function plural(n: number, unit: string): string {
  return `${n} ${unit}${n === 1 ? '' : 's'} ago`
}
