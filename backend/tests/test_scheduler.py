import logging

import pytest

import scheduler
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
        scheduler.run_forever(scrape=flaky_scrape, sleep=fake_sleep)

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
