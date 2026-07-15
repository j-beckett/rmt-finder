from datetime import datetime, timezone

from scraper.adapters.janeapp import JaneAppAdapter

# Clinic-local "now": 2026-07-14 18:00 PDT (-07:00). With LOOKAHEAD_DAYS=3 the
# window is the whole of the 14th, 15th, and 16th (today + 2 more days).
NOW = datetime.fromisoformat("2026-07-14T18:00:00-07:00")


def _within(start_at: str, now: datetime = NOW) -> bool:
    return JaneAppAdapter()._is_within_lookahead(start_at, now=now)


def test_slot_later_today_is_included(monkeypatch):
    monkeypatch.setenv("LOOKAHEAD_DAYS", "3")
    assert _within("2026-07-14T21:30:00-07:00")


def test_slot_on_the_last_whole_day_is_included(monkeypatch):
    monkeypatch.setenv("LOOKAHEAD_DAYS", "3")
    # Late on the 16th (day today+2) is still inside the floored window...
    assert _within("2026-07-16T23:00:00-07:00")


def test_slot_on_the_fourth_day_is_excluded(monkeypatch):
    monkeypatch.setenv("LOOKAHEAD_DAYS", "3")
    # ...but the 17th is a whole day past the window, even though it is < 72h
    # from `now` — the window is floored to calendar days, not rolling hours.
    assert not _within("2026-07-17T00:30:00-07:00")


def test_slot_in_the_past_is_excluded(monkeypatch):
    monkeypatch.setenv("LOOKAHEAD_DAYS", "3")
    assert not _within("2026-07-14T09:00:00-07:00")


def test_window_scales_with_lookahead_days(monkeypatch):
    monkeypatch.setenv("LOOKAHEAD_DAYS", "1")
    # Only today remains in a 1-day window.
    assert _within("2026-07-14T23:00:00-07:00")
    assert not _within("2026-07-15T09:00:00-07:00")


def test_malformed_start_at_is_excluded():
    assert not _within("not-a-timestamp")
