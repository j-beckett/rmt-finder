import type { Hit } from './analytics'

/** The parts of `window` the tracker touches, so tests can fake them. */
export interface TrackerWindow {
  goatcounter?: { count?: (vars: Hit) => void }
  document: { querySelector(selector: string): EventTarget | null }
}

export interface TrackerOptions {
  production: boolean
  optedOut: boolean
  win: TrackerWindow
}

/** A send(hit) that forwards to GoatCounter's count(). */
export function createTracker({
  production,
  optedOut,
  win,
}: TrackerOptions): (hit: Hit | null) => void {
  const send = (hit: Hit | null) => {
    if (!hit || !production || optedOut) return
    // Swallow everything: analytics must never break booking.
    try {
      if (win.goatcounter?.count) win.goatcounter.count(hit)
      // The tag is async and may not have run yet; a failed load never fires.
      else
        win.document
          .querySelector('script[data-goatcounter]')
          ?.addEventListener('load', () => send(hit), { once: true })
    } catch {
      // Dropped hit: an undercount, the safe direction.
    }
  }
  return send
}
