import { SlotGroups } from 'frontend'

const TZ = 'America/Vancouver'
const day = (n: number) => new Date(Date.now() + n * 86_400_000).toLocaleDateString('en-CA', { timeZone: TZ })

const slot = (n: number, hm: string, clinic: string, rmt: string, minutes = 60) => ({
  clinic_name: clinic,
  clinic_slug: clinic.toLowerCase().replace(/[^a-z]+/g, '-'),
  city: 'victoria',
  platform: 'jane',
  rmt_name: rmt,
  service_type: 'massage',
  treatment_name: `${minutes} Minute Massage`,
  duration_minutes: minutes,
  start_at: `${day(n)}T${hm}:00-07:00`,
  booking_url: 'https://example.janeapp.com/',
})

const today = [
  slot(0, '10:30', 'Fern & Stone Massage', 'Priya Natarajan'),
  slot(0, '14:00', 'Harbourview Wellness', 'Marcus Lee', 90),
]
const later = [
  slot(1, '09:00', 'Cedar Hill Therapeutics', 'Hannah Okafor', 45),
  slot(2, '13:30', 'Fern & Stone Massage', 'Daniel Ruiz'),
]

export const SingleDay = () => (
  <div className="mx-auto max-w-3xl px-4 py-6">
    <SlotGroups slots={today} today={day(0)} showDayBadges={false} />
  </div>
)

export const WithDayBadges = () => (
  <div className="mx-auto max-w-3xl px-4 py-6">
    <SlotGroups slots={[...today, ...later]} today={day(0)} showDayBadges />
  </div>
)
