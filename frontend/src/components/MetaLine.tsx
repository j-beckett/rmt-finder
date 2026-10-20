import type { AvailabilityResponse } from '@/lib/api'
import { timeAgo } from '@/lib/format'

export function MetaLine({
  data,
  nowMs,
  latestCheckOk,
  quietNote,
}: {
  data: AvailabilityResponse
  nowMs: number
  latestCheckOk: boolean
  quietNote: string | null
}) {
  const failed = data.failed_clinics.length
  return (
    <div className="mt-3 text-sm text-moss">
      <p>
        Last updated {timeAgo(data.scraped_at!, nowMs)}
        {failed === 0 && latestCheckOk && ' · all clinics checked'}
      </p>
      {quietNote && <p className="mt-0.5">{quietNote}</p>}
      {failed > 0 && (
        <p className="mt-0.5">
          {failed} of {data.clinics_attempted ?? '?'} clinics couldn't be
          checked — some openings may be missing.
        </p>
      )}
    </div>
  )
}
