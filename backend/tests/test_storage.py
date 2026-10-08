import sqlite3

import pytest

from scraper.models import AvailabilityResult, ServiceType
from storage import SchemaOutOfDateError, Storage
from tests.helpers import migrated_storage


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


def user_version(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("PRAGMA user_version").fetchone()[0]


def test_migrate_creates_schema_and_sets_version(tmp_path):
    db_path = tmp_path / "test.db"

    version = Storage(str(db_path)).migrate()

    assert {"scrape_runs", "slots"} <= table_names(db_path)
    assert version == 1
    assert user_version(db_path) == 1


def test_migrate_is_idempotent_and_keeps_data(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))
    storage.migrate()
    storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )

    assert storage.migrate() == 1

    assert storage.latest_run() is not None


def test_migrate_adopts_pre_versioning_database(tmp_path):
    # A database created before versioning existed: tables and rows present,
    # user_version still 0. This is what production looks like on first deploy.
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE scrape_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT NOT NULL,
                clinics_attempted INTEGER NOT NULL,
                clinics_succeeded INTEGER NOT NULL,
                failed_clinics TEXT NOT NULL
            );
            CREATE TABLE slots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL REFERENCES scrape_runs(id),
                clinic_name TEXT NOT NULL,
                city TEXT NOT NULL,
                platform TEXT NOT NULL,
                rmt_name TEXT NOT NULL,
                service_type TEXT NOT NULL,
                treatment_name TEXT NOT NULL,
                duration_minutes INTEGER NOT NULL,
                start_at TEXT NOT NULL,
                booking_url TEXT NOT NULL
            );
            INSERT INTO scrape_runs VALUES
                (1, '2026-07-09T10:00:00+00:00', '2026-07-09T10:01:30+00:00',
                 3, 3, '[]');
            """
        )
    assert user_version(db_path) == 0

    storage = migrated_storage(str(db_path))

    assert user_version(db_path) == 1
    assert storage.latest_run().id == 1


def test_constructor_does_not_touch_the_schema(tmp_path):
    db_path = tmp_path / "test.db"

    Storage(str(db_path))

    assert table_names(db_path) == set()
    assert user_version(db_path) == 0


def test_connect_closes_the_connection_on_exit(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))

    with storage._connect() as conn:
        conn.execute("SELECT 1")

    with pytest.raises(sqlite3.ProgrammingError):
        conn.execute("SELECT 1")


def test_connections_wait_for_locks_instead_of_failing_immediately(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))

    with storage._connect() as conn:
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]

    assert timeout_ms == 10_000


def test_connect_commits_on_success_and_rolls_back_on_error(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))
    insert = (
        "INSERT INTO scrape_runs (started_at, finished_at, clinics_attempted,"
        " clinics_succeeded, failed_clinics) VALUES ('a', 'b', 1, 1, '[]')"
    )

    with storage._connect() as conn:
        conn.execute(insert)
    with pytest.raises(RuntimeError):
        with storage._connect() as conn:
            conn.execute(insert)
            raise RuntimeError("boom")

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM scrape_runs").fetchone()[0] == 1


def test_require_current_raises_when_schema_is_behind(tmp_path):
    storage = Storage(str(tmp_path / "test.db"))

    with pytest.raises(SchemaOutOfDateError, match="migrate.py"):
        storage.require_current()


def test_require_current_passes_after_migrate(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))

    storage.require_current()


def test_migrate_enables_wal_mode(tmp_path):
    db_path = tmp_path / "test.db"

    Storage(str(db_path)).migrate()

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0] == "wal"


def test_migrate_applies_only_pending_migrations(tmp_path, monkeypatch):
    import storage as storage_module

    db_path = tmp_path / "test.db"
    Storage(str(db_path)).migrate()
    monkeypatch.setattr(
        storage_module,
        "MIGRATIONS",
        storage_module.MIGRATIONS + [["CREATE TABLE extra (id INTEGER)"]],
    )

    version = Storage(str(db_path)).migrate()

    assert version == 2
    assert user_version(db_path) == 2
    assert "extra" in table_names(db_path)


def test_failed_migration_rolls_back_completely(tmp_path, monkeypatch):
    import storage as storage_module

    db_path = tmp_path / "test.db"
    Storage(str(db_path)).migrate()
    monkeypatch.setattr(
        storage_module,
        "MIGRATIONS",
        storage_module.MIGRATIONS
        + [["CREATE TABLE half_done (id INTEGER)", "THIS IS NOT SQL"]],
    )

    with pytest.raises(sqlite3.OperationalError):
        Storage(str(db_path)).migrate()

    assert user_version(db_path) == 1
    assert "half_done" not in table_names(db_path)


def test_record_run_returns_id_and_persists_fields(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))

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
    storage = migrated_storage(str(db_path))
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
    storage = migrated_storage(str(db_path))
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
    storage = migrated_storage(str(tmp_path / "test.db"))

    assert storage.latest_good_run() is None


def test_latest_run_returns_newest_attempt_even_if_failed(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))
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
    storage = migrated_storage(str(tmp_path / "test.db"))

    assert storage.latest_run() is None


def test_insert_slots_persists_rows_with_run_fk(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))
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
