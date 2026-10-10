import type { Slot } from './slots'

/** One GoatCounter hit, in count()'s own shape. */
export interface Hit {
  path: string
  title: string
  event?: boolean
}

/** The slice of App state a page view depends on. */
export type ViewState =
  | { status: 'loading' }
  | { status: 'error'; unknownCity: boolean }
  | { status: 'ready'; data: { city: string; city_name: string } }

/** The page view for a settled availability state, or null to send nothing. */
export function pageView(state: ViewState, search: string): Hit | null {
  if (state.status === 'ready') {
    return { path: `/${state.data.city}`, title: state.data.city_name }
  }
  if (state.status === 'error' && state.unknownCity) {
    // One row for every bad link; the title shows which value broke it.
    const raw = new URLSearchParams(search).get('city') ?? ''
    return { path: '/unknown-city', title: `unknown city: ${raw}` }
  }
  return null
}

/** A Book click, keyed by the stable slug so renames don't split history. */
export function bookClick(slot: Slot): Hit | null {
  if (!slot.clinic_slug) return null
  return { path: `book/${slot.clinic_slug}`, title: slot.clinic_name, event: true }
}

/** Whether a click/auxclick on a slot card counts as a Book click. */
export function isTrackableClick(event: { type: string; button: number }): boolean {
  return (
    (event.type === 'click' && event.button === 0) ||
    (event.type === 'auxclick' && event.button === 1)
  )
}

type FlagStorage = Pick<Storage, 'getItem' | 'setItem' | 'removeItem'>

const OPT_OUT_KEY = 'rmt-notrack'

/** Apply ?notrack / ?notrack=off, then report whether this browser is opted out. */
export function optedOut(search: string, getStorage: () => FlagStorage): boolean {
  const params = new URLSearchParams(search)
  // Blocked storage (privacy modes, sandboxed frames) must never break the page.
  try {
    if (params.get('notrack') === 'off') {
      getStorage().removeItem(OPT_OUT_KEY)
      return false
    }
    if (params.has('notrack')) {
      getStorage().setItem(OPT_OUT_KEY, '1')
      return true
    }
    return getStorage().getItem(OPT_OUT_KEY) === '1'
  } catch {
    return false
  }
}
