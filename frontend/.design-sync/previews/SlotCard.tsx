import { SlotCard } from 'frontend'

const slot = (hm: string, clinic: string, rmt: string, minutes = 60) => ({
  clinic_name: clinic,
  clinic_slug: clinic.toLowerCase().replace(/[^a-z]+/g, '-'),
  city: 'victoria',
  platform: 'jane',
  rmt_name: rmt,
  service_type: 'massage',
  treatment_name: `${minutes} Minute Massage`,
  duration_minutes: minutes,
  start_at: `2026-07-17T${hm}:00-07:00`,
  booking_url: 'https://example.janeapp.com/',
})

export const Default = () => (
  <div className="mx-auto max-w-3xl px-4 py-6">
    <SlotCard slot={slot('10:30', 'Fern & Stone Massage', 'Priya Natarajan')} />
  </div>
)

// "Next available" highlight: a single card under a display heading.
export const NextAvailable = () => (
  <div className="mx-auto max-w-3xl px-4 py-6">
    <h2 className="display text-2xl mb-3">Next available</h2>
    <SlotCard slot={slot('14:00', 'Harbourview Wellness', 'Marcus Lee', 90)} />
  </div>
)

export const LongClinicName = () => (
  <div className="mx-auto max-w-3xl px-4 py-6">
    <SlotCard slot={slot('17:15', 'Cedar Hill Therapeutics & Sports Injury Clinic', 'Hannah Okafor', 45)} />
  </div>
)
