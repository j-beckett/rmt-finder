import logging
from datetime import datetime, time, timezone

import pytest

import config
import scheduler
from config import QuietHours
from storage import SchemaOutOfDateError, Storage
from tests.helpers import migrated_storage


def test_failing_scrape_records_failed_run_and_does_not_raise(
    monkeypatch, tmp_path, caplog
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    migrated_storage(str(db_path))

    def exploding_scrape(city):
        raise RuntimeError("network down")

    with caplog.at_level(logging.ERROR):
        scheduler.run_once("vancouver", exploding_scrape)

    storage = Storage(str(db_path))
    assert storage.latest_run("victoria") is None
    run = storage.latest_run("vancouver")
    assert run is not None
    assert run.city == "vancouver"
    assert run.clinics_attempted == 0
    assert run.clinics_succeeded == 0
    assert run.failed_clinics == []
    assert run.started_at <= run.finished_at
    assert "network down" in caplog.text


def test_successful_scrape_is_called_once_and_records_nothing_extra(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    migrated_storage(str(db_path))
    calls = []

    scheduler.run_once("victoria", lambda city: calls.append(city))

    assert calls == ["victoria"]
    assert Storage(str(db_path)).latest_run("victoria") is None


def test_run_forever_scrapes_every_city_then_sleeps_the_interval(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    migrated_storage(str(tmp_path / "test.db"))
    monkeypatch.setenv("SCRAPE_INTERVAL_MINUTES", "5")
    events = []

    def fake_scrape(city):
        events.append(f"scrape:{city}")

    def fake_sleep(seconds):
        events.append(("sleep", seconds))
        if events.count(("sleep", seconds)) == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(
            scrape=fake_scrape, sleep=fake_sleep, cities=["calgary", "victoria"]
        )

    assert events == [
        "scrape:calgary",
        "scrape:victoria",
        ("sleep", 300),
        "scrape:calgary",
        "scrape:victoria",
        ("sleep", 300),
    ]


def test_run_forever_continues_to_next_cycle_after_failing_scrape(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    migrated_storage(str(db_path))
    calls = []

    def flaky_scrape(city):
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")

    def fake_sleep(seconds):
        if len(calls) == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(
            scrape=flaky_scrape, sleep=fake_sleep, cities=["victoria"]
        )

    assert len(calls) == 2
    run = Storage(str(db_path)).latest_run("victoria")
    assert run.clinics_succeeded == 0


def test_run_forever_refuses_to_start_on_a_stale_schema(monkeypatch, tmp_path):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "unmigrated.db"))
    calls = []

    def stop_after_first_cycle(seconds):
        raise KeyboardInterrupt

    with pytest.raises(SchemaOutOfDateError, match="migrate.py"):
        scheduler.run_forever(scrape=lambda: calls.append(1), sleep=stop_after_first_cycle)

    assert calls == []


def test_run_cycle_scrapes_cities_in_order_and_isolates_a_failing_city(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    migrated_storage(str(db_path))
    calls = []

    def scrape(city):
        calls.append(city)
        if city == "vancouver":
            raise RuntimeError("vancouver is down")

    scheduler.run_cycle(scrape, ["calgary", "vancouver", "victoria"])

    assert calls == ["calgary", "vancouver", "victoria"]
    storage = Storage(str(db_path))
    assert storage.latest_run("vancouver").clinics_succeeded == 0
    assert storage.latest_run("victoria") is None  # fake scrape records nothing


OVERNIGHT = QuietHours(time(23, 0), time(6, 0))
THREE_AM_VANCOUVER = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)
NOON_VANCOUVER = datetime(2026, 10, 9, 19, 0, tzinfo=timezone.utc)


def test_run_once_skips_a_city_in_quiet_hours_and_records_nothing(
    monkeypatch, tmp_path, caplog
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    migrated_storage(str(db_path))
    calls = []

    with caplog.at_level(logging.INFO):
        scheduler.run_once(
            "victoria",
            lambda city: calls.append(city),
            quiet=OVERNIGHT,
            clock=lambda: THREE_AM_VANCOUVER,
        )

    assert calls == []
    assert Storage(str(db_path)).latest_run("victoria") is None
    assert "Quiet hours: skipping victoria" in caplog.text


def test_run_cycle_checks_quiet_hours_per_city_in_its_own_zone(
    monkeypatch, tmp_path
):
    # 12:30 UTC is 05:30 in Victoria (quiet) but 06:30 in Calgary (not).
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    migrated_storage(str(tmp_path / "test.db"))
    monkeypatch.setattr(
        config,
        "CITY_TIMEZONES",
        {"Victoria": "America/Vancouver", "Calgary": "America/Edmonton"},
    )
    calls = []

    scheduler.run_cycle(
        lambda city: calls.append(city),
        ["calgary", "victoria"],
        quiet=OVERNIGHT,
        clock=lambda: datetime(2026, 10, 9, 12, 30, tzinfo=timezone.utc),
    )

    assert calls == ["calgary"]


def stop_at_first_sleep(seconds):
    raise KeyboardInterrupt


def test_run_forever_applies_quiet_hours_from_settings(monkeypatch, tmp_path):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    migrated_storage(str(tmp_path / "test.db"))
    monkeypatch.setenv("QUIET_HOURS_START", "23:00")
    monkeypatch.setenv("QUIET_HOURS_END", "06:00")
    calls = []

    with pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(
            scrape=lambda city: calls.append(city),
            sleep=stop_at_first_sleep,
            cities=["victoria"],
            clock=lambda: THREE_AM_VANCOUVER,
        )

    assert calls == []


def test_run_forever_refuses_to_start_on_bad_quiet_hours(monkeypatch, tmp_path):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    migrated_storage(str(tmp_path / "test.db"))
    monkeypatch.setenv("QUIET_HOURS_START", "23:00")
    monkeypatch.delenv("QUIET_HOURS_END", raising=False)
    calls = []

    with pytest.raises(ValueError, match="QUIET_HOURS_END"):
        scheduler.run_forever(
            scrape=lambda city: calls.append(city),
            sleep=stop_at_first_sleep,
            cities=["victoria"],
        )

    assert calls == []


def test_run_forever_warns_about_a_suspiciously_long_quiet_window(
    monkeypatch, tmp_path, caplog
):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    migrated_storage(str(tmp_path / "test.db"))
    monkeypatch.setenv("QUIET_HOURS_START", "22:00")
    monkeypatch.setenv("QUIET_HOURS_END", "20:20")

    with caplog.at_level(logging.WARNING), pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(
            scrape=lambda city: None,
            sleep=stop_at_first_sleep,
            cities=["victoria"],
            clock=lambda: NOON_VANCOUVER,
        )

    assert "22h20m" in caplog.text
