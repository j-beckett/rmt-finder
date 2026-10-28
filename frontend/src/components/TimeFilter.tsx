import { timeFilterPick } from '@/lib/analytics'
import type { TimeOfDay } from '@/lib/slots'
import { send } from '@/lib/track'

const OPTIONS: { key: TimeOfDay; label: string }[] = [
  { key: 'morning', label: 'Morning' },
  { key: 'afternoon', label: 'Afternoon' },
  { key: 'evening', label: 'Evening' },
]

export function TimeFilter({
  active,
  onChange,
}: {
  active: TimeOfDay | null
  onChange: (time: TimeOfDay | null) => void
}) {
  // Tapping the active segment clears it, so the bar needs no "Any" option.
  const pick = (key: TimeOfDay) => {
    if (key === active) return onChange(null)
    send(timeFilterPick(key))
    onChange(key)
  }
  return (
    <div role="group" aria-label="Time of day" className="time-seg">
      {OPTIONS.map(({ key, label }) => (
        <button
          key={key}
          type="button"
          aria-pressed={key === active}
          onClick={() => pick(key)}
        >
          {label}
        </button>
      ))}
    </div>
  )
}
