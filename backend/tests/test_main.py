import sqlite3
from datetime import datetime, timedelta, timezone

import main as main_module
from scraper.models import AvailabilityResult, RunResult, ServiceType
from storage import Storage
from tests.helpers import migrated_storage


def make_slot():
    return AvailabilityResult(
        clinic_name="Good Clinic",
        clinic_slug="good-clinic",
        city="victoria",
        platform="janeapp",
        rmt_name="Jane Doe",
        service_type=ServiceType.MASSAGE_THERAPY,
        treatment_name="60min Massage",
        duration_minutes=60,
        start_at="2026-07-10T09:00:00-07:00",
        booking_url="https://example.com/book",
    )


def test_main_writes_snapshot_and_prints_summary(monkeypatch, capsys, tmp_path):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    monkeypatch.chdir(tmp_path)
    migrated_storage(str(db_path))
    fake_result = RunResult(
        slots=[make_slot()],
        attempted=["Good Clinic", "Broken Clinic"],
        succeeded=["Good Clinic"],
        failed=["Broken Clinic"],
    )
    monkeypatch.setattr(main_module, "run_all", lambda city=None: fake_result)

    main_module.main()

    run, slots = Storage(str(db_path)).latest_good_run("victoria")
    assert run.clinics_attempted == 2
    assert run.clinics_succeeded == 1
    assert run.failed_clinics == ["Broken Clinic"]
    assert run.started_at <= run.finished_at
    assert slots == [make_slot()]

    out = capsys.readouterr().out
    assert f"Run {run.id}: 2 clinics attempted, 1 succeeded, 1 failed" in out
    assert "Failed clinics: Broken Clinic" in out
    assert "1 slot(s) recorded" in out

    assert list(tmp_path.rglob("*.json")) == []


def test_cli_migrates_a_fresh_database_before_scraping(monkeypatch, tmp_path):
    # The local `python main.py` workflow must keep working on a brand-new
    # database without a separate migrate step.
    db_path = tmp_path / "fresh.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        main_module,
        "run_all",
        lambda city=None: RunResult(
            slots=[make_slot()],
            attempted=["Good Clinic"],
            succeeded=["Good Clinic"],
            failed=[],
        ),
    )

    main_module.cli()

    run, _ = Storage(str(db_path)).latest_good_run("victoria")
    assert run.clinics_succeeded == 1


def fake_run_all_recording(calls):
    def fake(city=None):
        calls.append(city)
        return RunResult(
            slots=[make_slot()],
            attempted=["Good Clinic"],
            succeeded=["Good Clinic"],
            failed=[],
        )

    return fake


def test_scrape_city_scrapes_that_city_and_records_a_run_for_it(
    monkeypatch, tmp_path
):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    storage = migrated_storage(str(db_path))
    calls = []
    monkeypatch.setattr(main_module, "run_all", fake_run_all_recording(calls))

    main_module.scrape_city("vancouver")

    assert calls == ["vancouver"]
    assert storage.latest_run("vancouver").clinics_succeeded == 1
    assert storage.latest_run("victoria") is None


def test_main_scrapes_every_city_in_the_roster(monkeypatch, tmp_path):
    from types import SimpleNamespace

    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    storage = migrated_storage(str(db_path))
    calls = []
    monkeypatch.setattr(main_module, "run_all", fake_run_all_recording(calls))
    monkeypatch.setattr(
        main_module,
        "CLINICS",
        [SimpleNamespace(city="Victoria"), SimpleNamespace(city="vancouver")],
    )

    main_module.main()

    assert calls == ["vancouver", "victoria"]
    assert storage.latest_run("victoria") is not None
    assert storage.latest_run("vancouver") is not None


def record_old_run(storage, days_ago, slots):
    """A good Victoria run that finished `days_ago` days ago, with `slots` slots."""
    finished_at = (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat()
    run_id = storage.record_run(
        city="victoria",
        started_at=finished_at,
        finished_at=finished_at,
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )
    storage.insert_slots(run_id, [make_slot() for _ in range(slots)])
    return run_id


def slot_run_ids(db_path):
    with sqlite3.connect(db_path) as conn:
        return {row[0] for row in conn.execute("SELECT DISTINCT run_id FROM slots")}


def test_scrape_city_prunes_old_slots_after_a_successful_scrape(
    monkeypatch, capsys, tmp_path
):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("RMT_FINDER_DB_PATH", db_path)
    monkeypatch.delenv("RETENTION_DAYS", raising=False)
    storage = migrated_storage(db_path)
    old_run = record_old_run(storage, days_ago=10, slots=3)
    monkeypatch.setattr(main_module, "run_all", fake_run_all_recording([]))

    main_module.scrape_city("victoria")

    new_run = storage.latest_run("victoria").id
    assert slot_run_ids(db_path) == {new_run}
    assert old_run != new_run
    assert "Pruned 3 slot(s) older than 7 day(s)" in capsys.readouterr().out


def test_scrape_city_does_not_prune_when_no_clinic_succeeded(
    monkeypatch, capsys, tmp_path
):
    # Two old good runs: the newer one is protected as the latest good run
    # anyway, so only the older one shows whether a failed scrape pruned.
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("RMT_FINDER_DB_PATH", db_path)
    monkeypatch.delenv("RETENTION_DAYS", raising=False)
    storage = migrated_storage(db_path)
    older = record_old_run(storage, days_ago=12, slots=2)
    latest_good = record_old_run(storage, days_ago=10, slots=2)
    monkeypatch.setattr(
        main_module,
        "run_all",
        lambda city=None: RunResult(
            slots=[], attempted=["Broken Clinic"], succeeded=[], failed=["Broken Clinic"]
        ),
    )

    main_module.scrape_city("victoria")

    assert slot_run_ids(db_path) == {older, latest_good}
    assert "Pruned" not in capsys.readouterr().out


def test_scrape_city_prints_nothing_about_pruning_when_nothing_was_old(
    monkeypatch, capsys, tmp_path
):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("RMT_FINDER_DB_PATH", db_path)
    monkeypatch.delenv("RETENTION_DAYS", raising=False)
    migrated_storage(db_path)
    monkeypatch.setattr(main_module, "run_all", fake_run_all_recording([]))

    main_module.scrape_city("victoria")

    assert "Pruned" not in capsys.readouterr().out
