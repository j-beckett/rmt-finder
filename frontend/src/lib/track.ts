import { optedOut } from './analytics'
import { createTracker } from './tracker'

/** The app's one tracker; opt-out is read once, since ?notrack comes with a full load. */
export const send = createTracker({
  production: import.meta.env.PROD,
  optedOut: optedOut(window.location.search, () => window.localStorage),
  win: window,
})
