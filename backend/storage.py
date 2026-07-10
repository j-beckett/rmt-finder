import json
import os
import sqlite3
from dataclasses import dataclass

from scraper.models import AvailabilityResult, ServiceType


@dataclass
class RunRecord:
    """A scrape_runs row read back from the database."""

    id: int
    started_at: str
    finished_at: str
    clinics_attempted: int
    clinics_succeeded: int
    failed_clinics: list[str]


SCHEMA = """
CREATE TABLE IF NOT EXISTS scrape_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT NOT NULL,
    finished_at TEXT NOT NULL,
    clinics_attempted INTEGER NOT NULL,
    clinics_succeeded INTEGER NOT NULL,
    failed_clinics TEXT NOT NULL
);

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
);
"""


class Storage:
    """Sole owner of all database access (SQLite now, swappable later)."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def record_run(
        self,
        started_at: str,
        finished_at: str,
        attempted: int,
        succeeded: int,
        failed_clinics: list[str],
    ) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                "INSERT INTO scrape_runs (started_at, finished_at,"
                " clinics_attempted, clinics_succeeded, failed_clinics)"
                " VALUES (?, ?, ?, ?, ?)",
                (
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

    @staticmethod
    def _run_record(row) -> RunRecord:
        return RunRecord(
            id=row[0],
            started_at=row[1],
            finished_at=row[2],
            clinics_attempted=row[3],
            clinics_succeeded=row[4],
            failed_clinics=json.loads(row[5]),
        )

    def latest_run(self) -> RunRecord | None:
        """Most recent run attempted, successful or not."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, started_at, finished_at, clinics_attempted,"
                " clinics_succeeded, failed_clinics FROM scrape_runs"
                " ORDER BY id DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return self._run_record(row)

    def latest_good_run(self) -> tuple[RunRecord, list[AvailabilityResult]] | None:
        """Latest run with at least one successful clinic, plus its slots.

        A newer zero-success run is skipped over, so this read is also the
        fallback the API serves when the latest attempt failed entirely.
        """
        with self._connect() as conn:
            run_row = conn.execute(
                "SELECT id, started_at, finished_at, clinics_attempted,"
                " clinics_succeeded, failed_clinics FROM scrape_runs"
                " WHERE clinics_succeeded > 0 ORDER BY id DESC LIMIT 1"
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
