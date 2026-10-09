import json
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from scraper.models import AvailabilityResult, ServiceType


@dataclass
class RunRecord:
    """A scrape_runs row read back from the database."""

    id: int
    city: str
    started_at: str
    finished_at: str
    clinics_attempted: int
    clinics_succeeded: int
    failed_clinics: list[str]


# How long a connection waits on another process's write lock before giving
# up. The API reads while the scheduler writes, so brief contention is normal.
BUSY_TIMEOUT_SECONDS = 10


class SchemaOutOfDateError(RuntimeError):
    """The database has fewer migrations applied than the code expects."""


# Ordered schema migrations; the schema version is the 1-based index of the
# last one applied (stored in PRAGMA user_version). Append, never edit: a
# migration that has shipped has already run against production. Migration 1
# is the original schema, kept IF NOT EXISTS so a database created before
# versioning existed (tables present, user_version 0) lands on version 1.
MIGRATIONS: list[list[str]] = [
    [
        """
        CREATE TABLE IF NOT EXISTS scrape_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT NOT NULL,
            clinics_attempted INTEGER NOT NULL,
            clinics_succeeded INTEGER NOT NULL,
            failed_clinics TEXT NOT NULL
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS slots (
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
        )
        """,
    ],
    [
        # Runs belong to a city. Existing rows were all Victoria runs, which
        # the default backfills; it stays as a safety net, and record_run()
        # still requires an explicit city so a forgotten one fails loudly.
        "ALTER TABLE scrape_runs ADD COLUMN city TEXT NOT NULL DEFAULT 'victoria'",
        # "Latest run for a city" and "slots of a run / of a city by time".
        "CREATE INDEX IF NOT EXISTS idx_scrape_runs_city_id"
        " ON scrape_runs (city, id)",
        "CREATE INDEX IF NOT EXISTS idx_slots_city_start_at"
        " ON slots (city, start_at)",
        "CREATE INDEX IF NOT EXISTS idx_slots_run_id ON slots (run_id)",
    ],
]


class Storage:
    """Sole owner of all database access (SQLite now, swappable later)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

    @contextmanager
    def _connect(self):
        """A short-lived connection: commit on success, roll back on error,
        always close. (sqlite3's own `with conn` commits/rolls back but
        leaves the connection open until garbage collected.)"""
        conn = sqlite3.connect(self.db_path, timeout=BUSY_TIMEOUT_SECONDS)
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def require_current(self) -> None:
        """Raise SchemaOutOfDateError unless every migration has been applied.

        Long-running processes call this at startup so a deploy that forgot
        to migrate fails loudly instead of on the first query.
        """
        with self._connect() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        if version < len(MIGRATIONS):
            raise SchemaOutOfDateError(
                f"Database schema is at version {version} but the code expects"
                f" {len(MIGRATIONS)}. Run: python backend/migrate.py"
            )

    def migrate(self) -> int:
        """Apply pending migrations in order; return the resulting version."""
        conn = sqlite3.connect(
            self.db_path, isolation_level=None, timeout=BUSY_TIMEOUT_SECONDS
        )
        try:
            # WAL lets the API read while the scheduler writes. It persists in
            # the database file, so setting it once here covers every later
            # connection; it can't be changed inside a transaction.
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("BEGIN IMMEDIATE")
            version = conn.execute("PRAGMA user_version").fetchone()[0]
            for number, statements in enumerate(MIGRATIONS, start=1):
                if number <= version:
                    continue
                for statement in statements:
                    conn.execute(statement)
                version = number
            conn.execute(f"PRAGMA user_version = {version}")
            conn.execute("COMMIT")
            return version
        finally:
            conn.close()

    def record_run(
        self,
        city: str,
        started_at: str,
        finished_at: str,
        attempted: int,
        succeeded: int,
        failed_clinics: list[str],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO scrape_runs (city, started_at, finished_at,"
                " clinics_attempted, clinics_succeeded, failed_clinics)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    city,
                    started_at,
                    finished_at,
                    attempted,
                    succeeded,
                    json.dumps(failed_clinics),
                ),
            )
            return cursor.lastrowid

    def insert_slots(self, run_id: int, slots: list[AvailabilityResult]) -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO slots (run_id, clinic_name, city, platform,"
                " rmt_name, service_type, treatment_name, duration_minutes,"
                " start_at, booking_url)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        run_id,
                        slot.clinic_name,
                        slot.city,
                        slot.platform,
                        slot.rmt_name,
                        slot.service_type.value,
                        slot.treatment_name,
                        slot.duration_minutes,
                        slot.start_at,
                        slot.booking_url,
                    )
                    for slot in slots
                ],
            )

    def prune_slots(
        self, city: str, retention_days: int, now: datetime | None = None
    ) -> int:
        """Delete a city's slots from runs that finished more than
        retention_days ago.

        Returns the number of slot rows deleted; retention_days <= 0 keeps
        everything. scrape_runs rows are never deleted (they are the health
        history). The city's latest good run is always kept, however old,
        because latest_good_run serves it when that city's scrapes keep
        failing. Scoped to one city so each scrape prunes only its own data.

        Runs below the oldest run_id still in slots have nothing left to
        delete, so they are skipped: the cost tracks the retention window,
        not the ever-growing scrape_runs history. (A city whose scrapes have
        failed for a long time holds that bound back via its protected run,
        which only widens the range scanned; results are unaffected.)

        julianday() parses the stored offset and compares instants in UTC, so
        a finished_at written with any offset is aged correctly (a string
        comparison only works while every writer uses +00:00). An unparseable
        timestamp gives NULL, so that run is kept. Postgres equivalent:
        finished_at::timestamptz < $1.
        """
        if retention_days <= 0:
            return 0
        now = now or datetime.now(timezone.utc)
        cutoff = (now - timedelta(days=retention_days)).isoformat()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM slots WHERE run_id IN ("
                " SELECT id FROM scrape_runs"
                " WHERE city = ? AND id >= (SELECT MIN(run_id) FROM slots)"
                " AND julianday(finished_at) < julianday(?)"
                " AND id NOT IN ("
                "  SELECT id FROM scrape_runs"
                "  WHERE city = ? AND clinics_succeeded > 0"
                "  ORDER BY id DESC LIMIT 1))",
                (city, cutoff, city),
            )
            return cursor.rowcount

    @staticmethod
    def _run_record(row) -> RunRecord:
        return RunRecord(
            id=row[0],
            city=row[1],
            started_at=row[2],
            finished_at=row[3],
            clinics_attempted=row[4],
            clinics_succeeded=row[5],
            failed_clinics=json.loads(row[6]),
        )

    def latest_run(self, city: str) -> RunRecord | None:
        """Most recent run attempted for a city, successful or not."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, city, started_at, finished_at, clinics_attempted,"
                " clinics_succeeded, failed_clinics FROM scrape_runs"
                " WHERE city = ? ORDER BY id DESC LIMIT 1",
                (city,),
            ).fetchone()
        if row is None:
            return None
        return self._run_record(row)

    def latest_good_run(
        self, city: str
    ) -> tuple[RunRecord, list[AvailabilityResult]] | None:
        """A city's latest run with at least one successful clinic, plus its slots.

        A newer zero-success run is skipped over, so this read is also the
        fallback the API serves when the latest attempt failed entirely.
        Scoped to the city so one city's failure never hides another's data.
        """
        with self._connect() as conn:
            run_row = conn.execute(
                "SELECT id, city, started_at, finished_at, clinics_attempted,"
                " clinics_succeeded, failed_clinics FROM scrape_runs"
                " WHERE city = ? AND clinics_succeeded > 0"
                " ORDER BY id DESC LIMIT 1",
                (city,),
            ).fetchone()
            if run_row is None:
                return None
            run = self._run_record(run_row)
            slot_rows = conn.execute(
                "SELECT clinic_name, city, platform, rmt_name, service_type,"
                " treatment_name, duration_minutes, start_at, booking_url"
                " FROM slots WHERE run_id = ? ORDER BY id",
                (run.id,),
            ).fetchall()
        slots = [
            AvailabilityResult(
                clinic_name=row[0],
                city=row[1],
                platform=row[2],
                rmt_name=row[3],
                service_type=ServiceType(row[4]),
                treatment_name=row[5],
                duration_minutes=row[6],
                start_at=row[7],
                booking_url=row[8],
            )
            for row in slot_rows
        ]
        return run, slots
