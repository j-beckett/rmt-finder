import { MetaLine } from 'frontend'

const now = Date.now()
const ago = (min: number) => new Date(now - min * 60_000).toISOString()

const envelope = (over = {}) => ({
  city: 'victoria',
  city_name: 'Victoria',
  scraped_at: ago(6),
  latest_attempt_at: ago(6),
  clinics_attempted: 14,
  failed_clinics: [] as string[],
  window_days: 3,
  timezone: 'America/Vancouver',
  clinics_total: 14,
  quiet_hours: null,
  slots: [],
  ...over,
})

export const AllChecked = () => (
  <MetaLine data={envelope()} nowMs={now} latestCheckOk quietNote={null} />
)

export const SomeClinicsFailed = () => (
  <MetaLine
    data={envelope({ failed_clinics: ['Fern & Stone Massage', 'Harbourview Wellness'] })}
    nowMs={now}
    latestCheckOk
    quietNote={null}
  />
)

export const QuietHours = () => (
  <MetaLine
    data={envelope({ scraped_at: ago(250), latest_attempt_at: ago(250) })}
    nowMs={now}
    latestCheckOk
    quietNote="We pause checks overnight and start again at 6:00 AM."
  />
)
