import { useEffect, useId, useRef, useState } from 'react'
import type { City } from '@/lib/api'
import { menuKey, openMenu, type MenuState } from '@/lib/menu'

export function CityMenu({
  cities,
  value,
  onChange,
}: {
  cities: City[]
  value: string | null
  onChange: (slug: string) => void
}) {
  const id = useId()
  const [menu, setMenu] = useState<MenuState>({ open: false, active: 0 })
  const wrapper = useRef<HTMLDivElement>(null)
  const button = useRef<HTMLButtonElement>(null)
  const list = useRef<HTMLUListElement>(null)
  const selected = cities.findIndex((c) => c.slug === value)
  const current = cities[selected]

  useEffect(() => {
    if (!menu.open) return
    list.current?.focus()
    // A click anywhere outside the menu closes it.
    const onPointerDown = (event: PointerEvent) => {
      if (!wrapper.current?.contains(event.target as Node)) {
        setMenu((m) => ({ ...m, open: false }))
      }
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [menu.open])

  function choose(index: number) {
    setMenu({ open: false, active: index })
    button.current?.focus()
    if (index !== selected) onChange(cities[index].slug)
  }

  function onKeyDown(event: React.KeyboardEvent) {
    const result = menuKey(menu, event.key, cities.length, selected)
    if (result.handled) event.preventDefault()
    setMenu(result.state)
    if (result.choose !== undefined) choose(result.choose)
    else if (result.focusButton) button.current?.focus()
  }

  return (
    <div ref={wrapper} className="city-menu mt-4">
      <div className="relative inline-block">
        <button
          ref={button}
          type="button"
          className="city-menu-button"
          aria-haspopup="listbox"
          aria-expanded={menu.open}
          aria-controls={`${id}-list`}
          onClick={() =>
            setMenu(menu.open ? { ...menu, open: false } : openMenu(selected))
          }
          onKeyDown={onKeyDown}
        >
          {current ? 'Change city' : 'Choose a city'}
          <ChevronIcon />
        </button>
        {menu.open && (
          <ul
            ref={list}
            id={`${id}-list`}
            role="listbox"
            aria-label="City"
            tabIndex={-1}
            aria-activedescendant={`${id}-${menu.active}`}
            className="city-menu-list"
            onKeyDown={onKeyDown}
          >
            {cities.map((c, i) => (
              <li
                key={c.slug}
                id={`${id}-${i}`}
                role="option"
                aria-selected={i === selected}
                data-active={i === menu.active}
                onPointerEnter={() => setMenu({ open: true, active: i })}
                onClick={() => choose(i)}
              >
                {c.name}
                {i === selected && <span aria-hidden="true">✓</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

function ChevronIcon() {
  return (
    <svg
      aria-hidden="true"
      className="city-menu-chevron"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 9l6 6 6-6" />
    </svg>
  )
}
