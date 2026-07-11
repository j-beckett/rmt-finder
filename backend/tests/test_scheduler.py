import logging

import pytest

import scheduler
from storage import Storage


def test_failing_scrape_records_failed_run_and_does_not_raise(
    monkeypatch, tmp_path, caplog
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))

    def exploding_scrape():
        raise RuntimeError("network down")

    with caplog.at_level(logging.ERROR):
        scheduler.run_once(scrape=exploding_scrape)

    run = Storage(str(db_path)).latest_run()
    assert run is not None
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
    calls = []

    scheduler.run_once(scrape=lambda: calls.append(1))

    assert calls == [1]
    assert Storage(str(db_path)).latest_run() is None


def test_run_forever_scrapes_immediately_then_sleeps_interval(monkeypatch, tmp_path):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("SCRAPE_INTERVAL_MINUTES", "5")
    events = []

    def fake_scrape():
        events.append("scrape")

    def fake_sleep(seconds):
        events.append(("sleep", seconds))
        if events.count("scrape") == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(scrape=fake_scrape, sleep=fake_sleep)

    assert events == ["scrape", ("sleep", 300), "scrape", ("sleep", 300)]


def test_run_forever_continues_to_next_cycle_after_failing_scrape(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    calls = []

    def flaky_scrape():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("boom")

    def fake_sleep(seconds):
        if len(calls) == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        scheduler.run_forever(scrape=flaky_scrape, sleep=fake_sleep)

    assert len(calls) == 2
    run = Storage(str(db_path)).latest_run()
    assert run.clinics_succeeded == 0
