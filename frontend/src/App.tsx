import { useEffect, useState } from 'react'
import { fetchAvailability, type AvailabilityResponse } from '@/lib/api'
import { formatSlotDate, formatSlotTime, timeAgo } from '@/lib/format'
import { sortSlots } from '@/lib/slots'

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: AvailabilityResponse }

function App() {
  const [state, setState] = useState<State>({ status: 'loading' })

  useEffect(() => {
    fetchAvailability()
      .then((data) => setState({ status: 'ready', data }))
      .catch((error: Error) => setState({ status: 'error', message: error.message }))
  }, [])

  return (
    <main className="mx-auto max-w-3xl px-4 py-8">
      <header className="mb-6">
        <h1 className="text-2xl font-semibold">RMT availability in Victoria</h1>
        {state.status === 'ready' && state.data.scraped_at && (
          <p className="mt-1 text-sm text-gray-600">
            Last updated {timeAgo(state.data.scraped_at, Date.now())}
          </p>
        )}
      </header>

      {state.status === 'loading' && <p>Loading availability…</p>}

      {state.status === 'error' && (
        <p role="alert">Couldn't load availability: {state.message}</p>
      )}

      {state.status === 'ready' && <SlotList data={state.data} />}
    </main>
  )
}

function SlotList({ data }: { data: AvailabilityResponse }) {
  const slots = sortSlots(data.slots)

  if (slots.length === 0) {
    return <p>No appointments found in the next 24 hours.</p>
  }

  return (
    <ul className="divide-y divide-gray-200">
      {slots.map((slot, i) => (
        <li key={i} className="flex items-center gap-4 py-3">
          <div className="w-40 shrink-0">
            <div className="font-medium">{formatSlotTime(slot.start_at)}</div>
            <div className="text-sm text-gray-600">{formatSlotDate(slot.start_at)}</div>
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate font-medium">{slot.clinic_name}</div>
            <div className="truncate text-sm text-gray-600">
              {slot.rmt_name} · {slot.duration_minutes} min
            </div>
          </div>
          <a
            href={slot.booking_url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded border border-gray-300 px-3 py-1.5 text-sm font-medium hover:bg-gray-50"
          >
            Book
          </a>
        </li>
      ))}
    </ul>
  )
}

export default App
