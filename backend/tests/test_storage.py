import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from scraper.models import AvailabilityResult, ServiceType
from storage import MIGRATIONS, SchemaOutOfDateError, Storage
from tests.helpers import migrated_storage

LATEST = len(MIGRATIONS)


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
    assert version == LATEST
    assert user_version(db_path) == LATEST


def test_migrate_is_idempotent_and_keeps_data(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))
    storage.migrate()
    storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )

    assert storage.migrate() == LATEST

    assert storage.latest_run("victoria") is not None


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

    assert user_version(db_path) == LATEST
    assert storage.latest_run("victoria").id == 1


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

    assert version == LATEST + 1
    assert user_version(db_path) == LATEST + 1
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

    assert user_version(db_path) == LATEST
    assert "half_done" not in table_names(db_path)


def test_record_run_returns_id_and_persists_fields(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))

    run_id = storage.record_run(
        city="victoria",
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
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=2,
        failed_clinics=["ViVi Therapy"],
    )
    storage.insert_slots(run_id, [make_slot()])

    run, slots = storage.latest_good_run("victoria")

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
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=3,
        failed_clinics=[],
    )
    storage.insert_slots(good_run_id, [make_slot()])
    storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:15:00+00:00",
        finished_at="2026-07-09T10:16:30+00:00",
        attempted=3,
        succeeded=0,
        failed_clinics=["A", "B", "C"],
    )

    run, slots = storage.latest_good_run("victoria")

    assert run.id == good_run_id
    assert slots == [make_slot()]


def test_latest_good_run_returns_none_on_empty_db(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))

    assert storage.latest_good_run("victoria") is None


def test_latest_run_returns_newest_attempt_even_if_failed(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))
    storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=3,
        failed_clinics=[],
    )
    failed_run_id = storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:15:00+00:00",
        finished_at="2026-07-09T10:16:30+00:00",
        attempted=3,
        succeeded=0,
        failed_clinics=["A", "B", "C"],
    )

    run = storage.latest_run("victoria")

    assert run.id == failed_run_id
    assert run.clinics_succeeded == 0
    assert run.failed_clinics == ["A", "B", "C"]


def test_latest_run_returns_none_on_empty_db(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))

    assert storage.latest_run("victoria") is None


def test_insert_slots_persists_rows_with_run_fk(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))
    run_id = storage.record_run(
        city="victoria",
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


def test_migration_2_adds_city_and_backfills_existing_runs_as_victoria(
    tmp_path, monkeypatch
):
    import storage as storage_module

    db_path = tmp_path / "test.db"
    # Build a database exactly as production has it: schema version 1, with
    # a run recorded before runs knew about cities.
    with monkeypatch.context() as m:
        m.setattr(storage_module, "MIGRATIONS", storage_module.MIGRATIONS[:1])
        Storage(str(db_path)).migrate()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO scrape_runs (started_at, finished_at, clinics_attempted,"
            " clinics_succeeded, failed_clinics) VALUES ('a', 'b', 3, 3, '[]')"
        )
    assert user_version(db_path) == 1

    assert Storage(str(db_path)).migrate() == 2

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT city FROM scrape_runs").fetchall() == [
            ("victoria",)
        ]


def test_migration_2_creates_the_lookup_indexes(tmp_path):
    db_path = tmp_path / "test.db"
    migrated_storage(str(db_path))

    with sqlite3.connect(db_path) as conn:
        indexes = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'index'"
            )
        }

    assert {
        "idx_scrape_runs_city_id",
        "idx_slots_city_start_at",
        "idx_slots_run_id",
    } <= indexes


def test_record_run_persists_the_city(tmp_path):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))

    run_id = storage.record_run(
        city="vancouver",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=2,
        succeeded=2,
        failed_clinics=[],
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT city FROM scrape_runs WHERE id = ?", (run_id,)
        ).fetchone()
    assert row == ("vancouver",)


def test_record_run_requires_a_city(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))

    with pytest.raises(TypeError, match="city"):
        storage.record_run(
            started_at="2026-07-09T10:00:00+00:00",
            finished_at="2026-07-09T10:01:30+00:00",
            attempted=1,
            succeeded=1,
            failed_clinics=[],
        )


def record(storage, city, finished_at, succeeded=1):
    return storage.record_run(
        city=city,
        started_at=finished_at,
        finished_at=finished_at,
        attempted=1,
        succeeded=succeeded,
        failed_clinics=[],
    )


def test_latest_run_is_scoped_to_the_city(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))
    victoria_id = record(storage, "victoria", "2026-07-09T10:00:00+00:00")
    record(storage, "vancouver", "2026-07-09T10:05:00+00:00")

    run = storage.latest_run("victoria")

    assert run.id == victoria_id
    assert run.city == "victoria"
    assert storage.latest_run("nowhere") is None


def test_latest_good_run_is_scoped_to_the_city(tmp_path):
    storage = migrated_storage(str(tmp_path / "test.db"))
    victoria_id = record(storage, "victoria", "2026-07-09T10:00:00+00:00")
    storage.insert_slots(victoria_id, [make_slot(city="victoria")])
    vancouver_id = record(storage, "vancouver", "2026-07-09T10:05:00+00:00")
    storage.insert_slots(
        vancouver_id, [make_slot(city="vancouver", clinic_name="Van Clinic")]
    )
    # A newer total failure in Vancouver must not touch Victoria's good run,
    # and Vancouver falls back to its own earlier good run.
    record(storage, "vancouver", "2026-07-09T10:20:00+00:00", succeeded=0)

    victoria_run, victoria_slots = storage.latest_good_run("victoria")
    vancouver_run, vancouver_slots = storage.latest_good_run("vancouver")

    assert victoria_run.id == victoria_id
    assert [s.clinic_name for s in victoria_slots] == ["Test Clinic"]
    assert vancouver_run.id == vancouver_id
    assert [s.clinic_name for s in vancouver_slots] == ["Van Clinic"]
    assert storage.latest_good_run("nowhere") is None


# --- retention -------------------------------------------------------------

NOW = datetime(2026, 10, 8, 12, 0, tzinfo=timezone.utc)


def add_run(storage, finished_at, city="victoria", succeeded=1, slots=2):
    """A run that finished at `finished_at` (aware datetime or ISO string)
    with `slots` slot rows."""
    if isinstance(finished_at, datetime):
        finished_at = finished_at.isoformat()
    run_id = storage.record_run(
        city=city,
        started_at=finished_at,
        finished_at=finished_at,
        attempted=1,
        succeeded=succeeded,
        failed_clinics=[],
    )
    storage.insert_slots(run_id, [make_slot(city=city) for _ in range(slots)])
    return run_id


def slot_counts(db_path):
    """{run_id: number of slot rows} for every run that still has slots."""
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT run_id, COUNT(*) FROM slots GROUP BY run_id"
        ).fetchall()
    return dict(rows)


def test_prune_slots_deletes_slots_of_runs_older_than_retention(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    old = add_run(storage, NOW - timedelta(days=8))
    recent = add_run(storage, NOW - timedelta(days=6))
    newest = add_run(storage, NOW - timedelta(minutes=15))

    deleted = storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert deleted == 2
    assert slot_counts(db_path) == {recent: 2, newest: 2}
    assert old not in slot_counts(db_path)


def run_ids(db_path):
    with sqlite3.connect(db_path) as conn:
        return [row[0] for row in conn.execute("SELECT id FROM scrape_runs ORDER BY id")]


def test_prune_slots_keeps_every_scrape_run_row(tmp_path):
    # scrape_runs is the health history: tiny, and kept forever.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    ids = [add_run(storage, NOW - timedelta(days=d)) for d in (30, 8, 1)]

    storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert run_ids(db_path) == ids


def test_prune_slots_keeps_latest_good_run_even_when_older_than_cutoff(tmp_path):
    # Scrapes have been failing for 10 days: the last good run is the
    # fallback the API serves, so its slots must survive.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    older_good = add_run(storage, NOW - timedelta(days=12))
    latest_good = add_run(storage, NOW - timedelta(days=10))

    deleted = storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert deleted == 2
    assert slot_counts(db_path) == {latest_good: 2}
    assert older_good not in slot_counts(db_path)


def test_prune_slots_protects_latest_good_run_per_city(tmp_path):
    # Victoria scraped fine just now; Vancouver's scrapes have been failing
    # for 10 days. Vancouver's last good run is its fallback and must survive
    # even though Victoria has a newer good run.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    van_older = add_run(storage, NOW - timedelta(days=12), city="vancouver")
    van_latest = add_run(storage, NOW - timedelta(days=10), city="vancouver")
    vic_old = add_run(storage, NOW - timedelta(days=9), city="victoria")
    vic_latest = add_run(storage, NOW - timedelta(minutes=15), city="victoria")

    storage.prune_slots("vancouver", retention_days=7, now=NOW)
    storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert slot_counts(db_path) == {van_latest: 2, vic_latest: 2}
    assert van_older not in slot_counts(db_path)
    assert vic_old not in slot_counts(db_path)


def test_prune_slots_protection_skips_newer_zero_success_runs(tmp_path):
    # The newest run failed entirely; protection follows the latest *good*
    # run (what latest_good_run serves), not the latest attempt.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    latest_good = add_run(storage, NOW - timedelta(days=10))
    add_run(storage, NOW - timedelta(days=9), succeeded=0, slots=0)

    storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert slot_counts(db_path) == {latest_good: 2}


def test_prune_slots_compares_instants_not_strings_across_utc_offsets(tmp_path):
    # Cutoff is 2026-10-01T12:00+00:00. Each run's string sorts on the wrong
    # side of it; only comparing instants gets both right.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    newer = add_run(storage, "2026-10-01T11:00:00-07:00")  # 18:00 UTC: keep
    older = add_run(storage, "2026-10-01T13:00:00+05:00")  # 08:00 UTC: prune
    latest_good = add_run(storage, NOW)

    storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert slot_counts(db_path) == {newer: 2, latest_good: 2}
    assert older not in slot_counts(db_path)


def test_prune_slots_with_zero_retention_keeps_everything(tmp_path):
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    old = add_run(storage, NOW - timedelta(days=400))
    latest_good = add_run(storage, NOW)

    deleted = storage.prune_slots("victoria", retention_days=0, now=NOW)

    assert deleted == 0
    assert slot_counts(db_path) == {old: 2, latest_good: 2}


def test_prune_slots_keeps_runs_whose_finished_at_cannot_be_parsed(tmp_path):
    # Fail safe: if a timestamp can't be aged, don't delete on a guess.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    unparseable = add_run(storage, "not a timestamp")
    latest_good = add_run(storage, NOW)

    storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert slot_counts(db_path) == {unparseable: 2, latest_good: 2}


def test_prune_slots_only_touches_the_given_city(tmp_path):
    # Each city's scrape prunes its own slots; Vancouver's old slots wait
    # for Vancouver's next good scrape.
    db_path = str(tmp_path / "test.db")
    storage = migrated_storage(db_path)
    van_old = add_run(storage, NOW - timedelta(days=9), city="vancouver")
    van_latest = add_run(storage, NOW, city="vancouver")
    vic_old = add_run(storage, NOW - timedelta(days=9), city="victoria")
    vic_latest = add_run(storage, NOW, city="victoria")

    deleted = storage.prune_slots("victoria", retention_days=7, now=NOW)

    assert deleted == 2
    assert slot_counts(db_path) == {van_old: 2, van_latest: 2, vic_latest: 2}
    assert vic_old not in slot_counts(db_path)
