export interface MenuState {
  open: boolean
  /** Highlighted option while open (keyboard focus or hover). */
  active: number
}

export interface MenuKeyResult {
  state: MenuState
  /** Option index to choose, if the key picked one. */
  choose?: number
  /** Return focus to the trigger button (closing by Enter/Space/Escape). */
  focusButton: boolean
  /** Whether to preventDefault; Tab stays unhandled so focus moves on. */
  handled: boolean
}

/** Open at the selected option, or the first when none is selected. */
export function openMenu(selected: number): MenuState {
  return { open: true, active: Math.max(selected, 0) }
}

/** Listbox keyboard behaviour (WAI-ARIA select-only combobox pattern). */
export function menuKey(
  state: MenuState,
  key: string,
  count: number,
  selected: number,
): MenuKeyResult {
  const closed = { open: false, active: state.active }
  const result = (next: MenuState, extra: Partial<MenuKeyResult> = {}) => ({
    state: next,
    focusButton: false,
    handled: true,
    ...extra,
  })

  if (!state.open) {
    return key === 'ArrowDown' || key === 'ArrowUp'
      ? result(openMenu(selected))
      : result(state, { handled: false })
  }

  switch (key) {
    case 'ArrowDown':
      return result({ open: true, active: (state.active + 1) % count })
    case 'ArrowUp':
      return result({ open: true, active: (state.active - 1 + count) % count })
    case 'Home':
      return result({ open: true, active: 0 })
    case 'End':
      return result({ open: true, active: count - 1 })
    case 'Enter':
    case ' ':
      return result(closed, { choose: state.active, focusButton: true })
    case 'Escape':
      return result(closed, { focusButton: true })
    case 'Tab':
      return result(closed, { handled: false })
    default:
      return result(state, { handled: false })
  }
}
