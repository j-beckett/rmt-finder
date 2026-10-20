import { bookClick, isTrackableClick } from '@/lib/analytics'
import { formatDayLabel, formatShortDate, formatSlotTime } from '@/lib/format'
import { groupSlotsByDay, type Slot } from '@/lib/slots'
import { send } from '@/lib/track'

export function SlotGroups({
  slots,
  today,
  showDayBadges,
}: {
  slots: Slot[]
  today: string
  showDayBadges: boolean
}) {
  return (
    <>
      {groupSlotsByDay(slots).map(({ date, slots: daySlots }) => (
        <section key={date} className="mb-7">
          {showDayBadges && (
            <span className="day-badge">{formatDayLabel(date, today)}</span>
          )}
          <ul className="mt-3.5 grid gap-4 list-none p-0">
            {daySlots.map((slot, i) => (
              <li key={i}>
                <SlotCard slot={slot} />
              </li>
            ))}
          </ul>
        </section>
      ))}
    </>
  )
}

function SlotCard({ slot }: { slot: Slot }) {
  // Fire-and-forget: no preventDefault, so the link opens exactly as before.
  const onBookClick = (event: React.MouseEvent) => {
    if (isTrackableClick(event)) send(bookClick(slot))
  }
  return (
    <a
      className="slot-card"
      href={slot.booking_url}
      target="_blank"
      rel="noopener noreferrer"
      onClick={onBookClick}
      onAuxClick={onBookClick}
    >
      <span className="slot-time display">{formatSlotTime(slot.start_at)}</span>
      <span className="slot-date">{formatShortDate(slot.start_at)}</span>
      <span className="slot-clinic display">{slot.clinic_name}</span>
      <span className="slot-rmt">
        {slot.rmt_name} · {slot.duration_minutes} min
      </span>
      <span className="pill">Book ↗</span>
    </a>
  )
}
