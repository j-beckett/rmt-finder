from datetime import datetime, timedelta
from typing import NamedTuple
from zoneinfo import ZoneInfo

from config import QuietHours


def is_quiet(window: QuietHours | None, tz_name: str, now: datetime) -> bool:
    """True when `now` falls inside the quiet window, in the city's local time."""
    if window is None:
        return False
    local = now.astimezone(ZoneInfo(tz_name)).time()
    if window.start < window.end:
        return window.start <= local < window.end
    # Crosses midnight (the usual overnight case): quiet late and early.
    return local >= window.start or local < window.end


# Any real overnight pause is shorter than this; a longer window is valid but
# almost certainly a typo (e.g. 22:00 to 20:20 is 22h20m of no scraping).
LONG_WINDOW = timedelta(hours=12)


def window_length(window: QuietHours) -> timedelta:
    """How long the window lasts each day, including across midnight."""
    day = timedelta(days=1)
    start = timedelta(hours=window.start.hour, minutes=window.start.minute)
    end = timedelta(hours=window.end.hour, minutes=window.end.minute)
    return (end - start) % day


def long_window_warning(window: QuietHours | None) -> str | None:
    """A startup warning when quiet hours cover more than 12 hours a day."""
    if window is None:
        return None
    length = window_length(window)
    if length <= LONG_WINDOW:
        return None
    hours, minutes = divmod(int(length.total_seconds()) // 60, 60)
    return (
        f"Quiet hours {window.start:%H:%M}-{window.end:%H:%M} cover"
        f" {hours}h{minutes:02d}m a day; check QUIET_HOURS_START and"
        " QUIET_HOURS_END."
    )


class WindowTimes(NamedTuple):
    start: datetime
    end: datetime


def last_window(
    window: QuietHours | None, tz_name: str, now: datetime
) -> WindowTimes | None:
    """The latest quiet window that has started by `now`, as aware datetimes
    in the city's zone: the one in progress, or else the one that ended most
    recently. The API sends it so the frontend can tell "paused overnight"
    from "failing".

    Start and end are built from local dates and wall-clock times (not start
    plus a duration), so a clock change inside the window can't skew them.
    """
    if window is None:
        return None
    zone = ZoneInfo(tz_name)
    local_now = now.astimezone(zone)
    start_date = local_now.date()
    if local_now.time() < window.start:
        start_date -= timedelta(days=1)
    end_date = start_date if window.start < window.end else start_date + timedelta(days=1)
    return WindowTimes(
        datetime.combine(start_date, window.start, tzinfo=zone),
        datetime.combine(end_date, window.end, tzinfo=zone),
    )
