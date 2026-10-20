import { useState } from 'react'
import { Availability } from 'frontend'

// Dates are built in the city's zone so "Today"/"Tomorrow" pills always line up.
const TZ = 'America/Vancouver'
const day = (n: number) => new Date(Date.now() + n * 86_400_000).toLocaleDateString('en-CA', { timeZone: TZ })
const at = (n: number, hm: string) => `${day(n)}T${hm}:00-07:00`
const ago = (min: number) => new Date(Date.now() - min * 60_000).toISOString()

const slot = (n: number, hm: string, clinic: string, rmt: string, minutes = 60) => ({
  clinic_name: clinic,
  clinic_slug: clinic.toLowerCase().replace(/[^a-z]+/g, '-'),
  city: 'victoria',
  platform: 'jane',
  rmt_name: rmt,
  service_type: 'massage',
  treatment_name: `${minutes} Minute Massage`,
  duration_minutes: minutes,
  start_at: at(n, hm),
  booking_url: 'https://example.janeapp.com/',
})

const slots = [
  slot(0, '10:30', 'Fern & Stone Massage', 'Priya Natarajan'),
  slot(0, '14:00', 'Harbourview Wellness', 'Marcus Lee', 90),
  slot(0, '17:15', 'Cedar Hill Therapeutics', 'Hannah Okafor', 45),
  slot(1, '09:00', 'Fern & Stone Massage', 'Daniel Ruiz'),
  slot(2, '13:30', 'Harbourview Wellness', 'Marcus Lee'),
]

const envelope = (over = {}) => ({
  city: 'victoria',
  city_name: 'Victoria',
  scraped_at: ago(6),
  latest_attempt_at: ago(6),
  clinics_attempted: 14,
  failed_clinics: [] as string[],
  window_days: 3,
  timezone: TZ,
  clinics_total: 14,
  quiet_hours: null,
  slots,
  ...over,
})

// The app owns the active pill in state; previews do the same so pills stay clickable.
function Page({ data, start = 0 }: { data: ReturnType<typeof envelope>; start?: number | 'all' }) {
  const [win, setWin] = useState<number | 'all'>(start)
  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <Availability data={data} activeWindow={win} onWindowChange={setWin} />
    </div>
  )
}

export const Today = () => <Page data={envelope()} />
// One slot per day keeps the badge rhythm visible without overflowing the card.
export const AllDays = () => <Page data={envelope({ slots: [slots[0], slots[3]] })} start="all" />
export const StaleData = () => <Page data={envelope({ scraped_at: ago(75), latest_attempt_at: ago(75), slots: slots.slice(0, 2) })} />
export const LatestCheckFailed = () => <Page data={envelope({ scraped_at: ago(20), latest_attempt_at: ago(3) })} />
export const NothingToday = () => <Page data={envelope({ slots: slots.slice(3) })} />
export const NoOpenings = () => <Page data={envelope({ slots: [] })} />
