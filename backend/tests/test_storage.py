import sqlite3

from scraper.models import AvailabilityResult, ServiceType
from storage import Storage


def make_slot(**overrides):
    slot = AvailabilityResult(
        clinic_name="Test Clinic",
        city="victoria",
        platform="janeapp",
        rmt_name="Jane Doe",
        service_type=ServiceType.MASSAGE_THERAPY,
        treatment_name="60min Massage",
        duration_minutes=60,
        start_at="2026-07-10T09:00:00-07:00",
        booking_url="https://example.com/book",
    )
    for key, value in overrides.items():
        setattr(slot, key, value)
    return slot


def table_names(db_path):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    return {row[0] for row in rows}


def test_storage_initializes_schema(tmp_path):
    db_path = tmp_path / "test.db"

    Storage(str(db_path))

    assert {"scrape_runs", "slots"} <= table_names(db_path)


def test_record_run_returns_id_and_persists_fields(tmp_path):
    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))

    run_id = storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=2,
        failed_clinics=["ViVi Therapy"],
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT id, started_at, finished_at, clinics_attempted,"
            " clinics_succeeded, failed_clinics FROM scrape_runs"
        ).fetchone()

    assert row == (
        run_id,
        "2026-07-09T10:00:00+00:00",
        "2026-07-09T10:01:30+00:00",
        3,
        2,
        '["ViVi Therapy"]',
    )


def test_latest_good_run_round_trips_run_and_slots(tmp_path):
    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    run_id = storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=2,
        failed_clinics=["ViVi Therapy"],
    )
    storage.insert_slots(run_id, [make_slot()])

    run, slots = storage.latest_good_run()

    assert run.id == run_id
    assert run.started_at == "2026-07-09T10:00:00+00:00"
    assert run.finished_at == "2026-07-09T10:01:30+00:00"
    assert run.clinics_attempted == 3
    assert run.clinics_succeeded == 2
    assert run.failed_clinics == ["ViVi Therapy"]
    assert slots == [make_slot()]


def test_latest_good_run_skips_newer_zero_success_run(tmp_path):
    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    good_run_id = storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=3,
        failed_clinics=[],
    )
    storage.insert_slots(good_run_id, [make_slot()])
    storage.record_run(
        started_at="2026-07-09T10:15:00+00:00",
        finished_at="2026-07-09T10:16:30+00:00",
        attempted=3,
        succeeded=0,
        failed_clinics=["A", "B", "C"],
    )

    run, slots = storage.latest_good_run()

    assert run.id == good_run_id
    assert slots == [make_slot()]


def test_latest_good_run_returns_none_on_empty_db(tmp_path):
    storage = Storage(str(tmp_path / "test.db"))

    assert storage.latest_good_run() is None


def test_latest_run_returns_newest_attempt_even_if_failed(tmp_path):
    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=3,
        failed_clinics=[],
    )
    failed_run_id = storage.record_run(
        started_at="2026-07-09T10:15:00+00:00",
        finished_at="2026-07-09T10:16:30+00:00",
        attempted=3,
        succeeded=0,
        failed_clinics=["A", "B", "C"],
    )

    run = storage.latest_run()

    assert run.id == failed_run_id
    assert run.clinics_succeeded == 0
    assert run.failed_clinics == ["A", "B", "C"]


def test_latest_run_returns_none_on_empty_db(tmp_path):
    storage = Storage(str(tmp_path / "test.db"))

    assert storage.latest_run() is None


def test_insert_slots_persists_rows_with_run_fk(tmp_path):
    db_path = tmp_path / "test.db"
    storage = Storage(str(db_path))
    run_id = storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )

    storage.insert_slots(run_id, [make_slot(), make_slot(rmt_name="John Roe")])

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT run_id, clinic_name, city, platform, rmt_name,"
            " service_type, treatment_name, duration_minutes, start_at,"
            " booking_url FROM slots ORDER BY id"
        ).fetchall()

    assert rows == [
        (
            run_id,
            "Test Clinic",
            "victoria",
            "janeapp",
            "Jane Doe",
            "massage_therapy",
            "60min Massage",
            60,
            "2026-07-10T09:00:00-07:00",
            "https://example.com/book",
        ),
        (
            run_id,
            "Test Clinic",
            "victoria",
            "janeapp",
            "John Roe",
            "massage_therapy",
            "60min Massage",
            60,
            "2026-07-10T09:00:00-07:00",
            "https://example.com/book",
        ),
    ]
