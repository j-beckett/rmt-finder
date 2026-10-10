import { describe, expect, it, vi } from 'vitest'
import { createTracker, type TrackerWindow } from '../tracker'

const hit = { path: '/victoria', title: 'Victoria' }

function fakeWindow(count?: (vars: unknown) => void) {
  return {
    goatcounter: count ? { count } : undefined,
    document: { querySelector: () => null },
  }
}

describe('createTracker', () => {
  it('sends the hit through count() in production', () => {
    const count = vi.fn()
    const send = createTracker({ production: true, optedOut: false, win: fakeWindow(count) })
    send(hit)
    expect(count).toHaveBeenCalledWith(hit)
  })

  it('sends nothing when this browser is opted out', () => {
    const count = vi.fn()
    const send = createTracker({ production: true, optedOut: true, win: fakeWindow(count) })
    send(hit)
    expect(count).not.toHaveBeenCalled()
  })

  it('sends nothing outside a production build', () => {
    const count = vi.fn()
    const send = createTracker({ production: false, optedOut: false, win: fakeWindow(count) })
    send(hit)
    expect(count).not.toHaveBeenCalled()
  })

  it('does nothing when the script is absent (blocked, failed, not live)', () => {
    const send = createTracker({ production: true, optedOut: false, win: fakeWindow() })
    expect(() => send(hit)).not.toThrow()
  })

  it('never throws, even if count() does', () => {
    const count = () => {
      throw new Error('boom')
    }
    const send = createTracker({ production: true, optedOut: false, win: fakeWindow(count) })
    expect(() => send(hit)).not.toThrow()
  })

  it('sends a hit made before the async script ran once it loads', () => {
    const script = new EventTarget()
    const win: TrackerWindow = { document: { querySelector: () => script } }
    const send = createTracker({ production: true, optedOut: false, win })
    send(hit)

    const count = vi.fn()
    win.goatcounter = { count }
    script.dispatchEvent(new Event('load'))
    expect(count).toHaveBeenCalledExactlyOnceWith(hit)
  })
})
