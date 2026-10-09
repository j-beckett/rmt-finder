import { describe, expect, it } from 'vitest'
import { menuKey, openMenu } from '../menu'

const open = (active: number) => ({ open: true, active })

describe('openMenu', () => {
  it('starts on the selected option', () => {
    expect(openMenu(1)).toEqual(open(1))
  })

  it('starts on the first option when nothing is selected', () => {
    expect(openMenu(-1)).toEqual(open(0))
  })
})

describe('menuKey on a closed menu', () => {
  it('opens on ArrowDown or ArrowUp at the selected option', () => {
    expect(menuKey({ open: false, active: 0 }, 'ArrowDown', 3, 2).state).toEqual(open(2))
    expect(menuKey({ open: false, active: 0 }, 'ArrowUp', 3, 2).state).toEqual(open(2))
  })

  it('ignores other keys', () => {
    expect(menuKey({ open: false, active: 0 }, 'x', 3, 2).handled).toBe(false)
  })
})

describe('menuKey on an open menu', () => {
  it('moves down and up, wrapping at the ends', () => {
    expect(menuKey(open(0), 'ArrowDown', 3, 0).state).toEqual(open(1))
    expect(menuKey(open(2), 'ArrowDown', 3, 0).state).toEqual(open(0))
    expect(menuKey(open(0), 'ArrowUp', 3, 0).state).toEqual(open(2))
  })

  it('jumps with Home and End', () => {
    expect(menuKey(open(1), 'Home', 3, 0).state).toEqual(open(0))
    expect(menuKey(open(1), 'End', 3, 0).state).toEqual(open(2))
  })

  it('chooses the active option on Enter or Space, closes, and refocuses the button', () => {
    for (const key of ['Enter', ' ']) {
      const result = menuKey(open(1), key, 3, 0)
      expect(result.choose).toBe(1)
      expect(result.state.open).toBe(false)
      expect(result.focusButton).toBe(true)
    }
  })

  it('closes on Escape without choosing, and refocuses the button', () => {
    const result = menuKey(open(1), 'Escape', 3, 0)
    expect(result.choose).toBeUndefined()
    expect(result.state.open).toBe(false)
    expect(result.focusButton).toBe(true)
  })

  it('closes on Tab but lets focus move on naturally', () => {
    const result = menuKey(open(1), 'Tab', 3, 0)
    expect(result.state.open).toBe(false)
    expect(result.focusButton).toBe(false)
    expect(result.handled).toBe(false)
  })
})
