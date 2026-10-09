from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from config import QuietHours
from quiet_hours import is_quiet, last_window, long_window_warning

VANCOUVER = "America/Vancouver"
OVERNIGHT = QuietHours(time(23, 0), time(6, 0))


def test_never_quiet_when_quiet_hours_are_off():
    now = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)  # 3 am Vancouver

    assert is_quiet(None, VANCOUVER, now) is False


def vancouver(hour, minute=0, day=9):
    """A Vancouver wall-clock time on 2026-10-`day` (UTC-7 all of October)."""
    return datetime(2026, 10, day, hour, minute, tzinfo=ZoneInfo(VANCOUVER))


@pytest.mark.parametrize(
    "local, quiet",
    [
        (vancouver(22, 59), False),
        (vancouver(23, 0), True),  # start is inclusive
        (vancouver(23, 59), True),
        (vancouver(0, 0), True),  # across midnight
        (vancouver(3, 0), True),
        (vancouver(5, 59), True),
        (vancouver(6, 0), False),  # end is exclusive: the 6 am run scrapes
        (vancouver(12, 0), False),
    ],
)
def test_overnight_window_crossing_midnight(local, quiet):
    assert is_quiet(OVERNIGHT, VANCOUVER, local) is quiet


@pytest.mark.parametrize(
    "local, quiet",
    [
        (vancouver(0, 59), False),
        (vancouver(1, 0), True),
        (vancouver(4, 59), True),
        (vancouver(5, 0), False),
        (vancouver(23, 0), False),
    ],
)
def test_window_within_one_day(local, quiet):
    assert is_quiet(QuietHours(time(1, 0), time(5, 0)), VANCOUVER, local) is quiet


def test_uses_the_city_zone_not_utc_or_the_host():
    # 07:00 UTC is midnight in Vancouver (quiet) but 07:00 in UTC (not).
    now = datetime(2026, 10, 9, 7, 0, tzinfo=timezone.utc)

    assert is_quiet(OVERNIGHT, VANCOUVER, now) is True
    assert is_quiet(OVERNIGHT, "UTC", now) is False


def test_bc_permanent_utc_minus_7_after_2026_11_01():
    # No fall-back: 06:00 on 2 November is 13:00 UTC (stale tz data says 14:00).
    before_six = datetime(2026, 11, 2, 12, 59, tzinfo=timezone.utc)
    six_am = datetime(2026, 11, 2, 13, 0, tzinfo=timezone.utc)

    assert is_quiet(OVERNIGHT, VANCOUVER, before_six) is True
    assert is_quiet(OVERNIGHT, VANCOUVER, six_am) is False


def test_long_window_warning_flags_windows_over_12_hours():
    message = long_window_warning(QuietHours(time(22, 0), time(20, 20)))

    assert "22h20m" in message
    assert "QUIET_HOURS_START" in message and "QUIET_HOURS_END" in message


@pytest.mark.parametrize(
    "window",
    [
        None,
        OVERNIGHT,  # 7 hours
        QuietHours(time(20, 0), time(8, 0)),  # exactly 12 hours
        QuietHours(time(1, 0), time(5, 0)),
    ],
)
def test_long_window_warning_is_silent_for_normal_windows(window):
    assert long_window_warning(window) is None


@pytest.mark.parametrize(
    "now, start, end",
    [
        # Inside the window, after midnight: it started last night.
        (vancouver(3, 0), vancouver(23, 0, day=8), vancouver(6, 0)),
        # Inside the window, before midnight: it started tonight.
        (vancouver(23, 30), vancouver(23, 0), vancouver(6, 0, day=10)),
        # Daytime: the window that ended this morning.
        (vancouver(12, 0), vancouver(23, 0, day=8), vancouver(6, 0)),
        (vancouver(22, 59), vancouver(23, 0, day=8), vancouver(6, 0)),
    ],
)
def test_last_window_is_the_latest_one_that_has_started(now, start, end):
    assert last_window(OVERNIGHT, VANCOUVER, now) == (start, end)


def test_last_window_is_none_when_quiet_hours_are_off():
    assert last_window(None, VANCOUVER, vancouver(3, 0)) is None


@pytest.mark.parametrize(
    "now, start, end",
    [
        (vancouver(0, 30), vancouver(1, 0, day=8), vancouver(5, 0, day=8)),
        (vancouver(3, 0), vancouver(1, 0), vancouver(5, 0)),
    ],
)
def test_last_window_within_one_day(now, start, end):
    window = QuietHours(time(1, 0), time(5, 0))

    assert last_window(window, VANCOUVER, now) == (start, end)


def test_last_window_over_bcs_old_fall_back_night_ends_at_6_am_utc_minus_7():
    now = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)  # 3 am, 1 November

    start, end = last_window(OVERNIGHT, VANCOUVER, now)

    assert start == datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)  # 23:00 -7
    assert end == datetime(2026, 11, 1, 13, 0, tzinfo=timezone.utc)  # 06:00 -7
    assert end.utcoffset() == timedelta(hours=-7)


def test_last_window_ends_at_the_wall_clock_time_across_a_clock_change():
    # Spring-forward night: 6 real hours, but it must still end at 06:00 local.
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)  # 03:00 PDT

    start, end = last_window(OVERNIGHT, VANCOUVER, now)

    assert (start.hour, end.hour) == (23, 6)
    # Real elapsed time (same-zone subtraction would give wall-clock hours).
    assert end.astimezone(timezone.utc) - start.astimezone(timezone.utc) == timedelta(
        hours=6
    )
