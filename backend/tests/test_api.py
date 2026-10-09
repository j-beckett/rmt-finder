import logging
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scraper.models import AvailabilityResult, ServiceType
from storage import SchemaOutOfDateError
from tests.helpers import migrated_storage


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    # make_client overrides get_storage on the shared app; don't leak a
    # deleted tmp database into the next test.
    yield
    from api import app

    app.dependency_overrides.clear()


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


def make_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    storage = migrated_storage(str(db_path))

    from api import app, get_storage

    app.dependency_overrides[get_storage] = lambda: storage
    return TestClient(app), storage


def test_availability_envelope_carries_run_metadata(tmp_path, monkeypatch):
    client, storage = make_client(tmp_path, monkeypatch)
    run_id = storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=2,
        failed_clinics=["ViVi Therapy"],
    )
    storage.insert_slots(run_id, [make_slot()])

    body = client.get("/api/availability").json()

    assert body["scraped_at"] == "2026-07-09T10:01:30+00:00"
    assert body["latest_attempt_at"] == "2026-07-09T10:01:30+00:00"
    assert body["clinics_attempted"] == 3
    assert body["failed_clinics"] == ["ViVi Therapy"]


def test_availability_falls_back_when_latest_attempt_failed_entirely(
    tmp_path, monkeypatch
):
    client, storage = make_client(tmp_path, monkeypatch)
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

    body = client.get("/api/availability").json()

    assert body["scraped_at"] == "2026-07-09T10:01:30+00:00"
    assert body["latest_attempt_at"] == "2026-07-09T10:16:30+00:00"
    assert body["latest_attempt_at"] > body["scraped_at"]
    assert len(body["slots"]) == 1
    assert body["failed_clinics"] == []


def test_empty_but_successful_run_returns_empty_slots_with_normal_envelope(
    tmp_path, monkeypatch
):
    client, storage = make_client(tmp_path, monkeypatch)
    storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=3,
        failed_clinics=[],
    )

    body = client.get("/api/availability").json()

    assert body["slots"] == []
    assert body["scraped_at"] == "2026-07-09T10:01:30+00:00"
    assert body["latest_attempt_at"] == body["scraped_at"]
    assert body["failed_clinics"] == []


def test_empty_database_returns_empty_slots_and_null_timestamps(
    tmp_path, monkeypatch
):
    client, _ = make_client(tmp_path, monkeypatch)

    response = client.get("/api/availability")

    assert response.status_code == 200
    body = response.json()
    assert body["slots"] == []
    assert body["scraped_at"] is None
    assert body["latest_attempt_at"] is None


def use_cities(monkeypatch, *cities):
    """Make the API's clinic roster contain one clinic per given city."""
    import api


    monkeypatch.setattr(
        api, "CLINICS", [SimpleNamespace(city=city) for city in cities]
    )


def record_city_run(storage, city, clinic_name):
    run_id = storage.record_run(
        city=city,
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )
    storage.insert_slots(run_id, [make_slot(city=city, clinic_name=clinic_name)])


def test_city_param_picks_that_citys_run_and_defaults_to_victoria(
    tmp_path, monkeypatch
):
    use_cities(monkeypatch, "victoria", "vancouver")
    client, storage = make_client(tmp_path, monkeypatch)
    record_city_run(storage, "victoria", "Victoria Clinic")
    record_city_run(storage, "vancouver", "Vancouver Clinic")

    default = client.get("/api/availability").json()
    van = client.get("/api/availability", params={"city": "VANCOUVER"}).json()

    assert [s["clinic_name"] for s in default["slots"]] == ["Victoria Clinic"]
    assert [s["clinic_name"] for s in van["slots"]] == ["Vancouver Clinic"]


def test_unknown_city_is_a_404_not_an_empty_success(tmp_path, monkeypatch):
    use_cities(monkeypatch, "victoria")
    client, _ = make_client(tmp_path, monkeypatch)

    response = client.get("/api/availability", params={"city": "atlantis"})

    assert response.status_code == 404
    assert "atlantis" in response.json()["detail"]


def test_clinic_count_and_timezone_are_per_city(tmp_path, monkeypatch):
    import config

    use_cities(monkeypatch, "victoria", "victoria", "toronto")
    monkeypatch.setattr(
        config,
        "CITY_TIMEZONES",
        {"Victoria": "America/Vancouver", "Toronto": "America/Toronto"},
    )
    client, _ = make_client(tmp_path, monkeypatch)

    victoria = client.get("/api/availability").json()
    toronto = client.get("/api/availability", params={"city": "toronto"}).json()

    assert (victoria["clinics_total"], victoria["timezone"]) == (
        2,
        "America/Vancouver",
    )
    assert (toronto["clinics_total"], toronto["timezone"]) == (1, "America/Toronto")


def test_envelope_carries_the_configured_clinic_count(tmp_path, monkeypatch):
    from scraper.clinics import CLINICS

    client, _ = make_client(tmp_path, monkeypatch)

    body = client.get("/api/availability").json()

    assert body["clinics_total"] == len(CLINICS)


def test_frontend_build_is_served_from_root_when_present(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>rmt finder shell</html>")
    monkeypatch.setenv("RMT_FINDER_FRONTEND_DIST", str(dist))

    from api import mount_frontend

    app = FastAPI()
    mount_frontend(app)

    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "rmt finder shell" in response.text


def test_frontend_mount_is_skipped_when_no_build_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("RMT_FINDER_FRONTEND_DIST", str(tmp_path / "missing"))

    from api import mount_frontend

    app = FastAPI()
    mount_frontend(app)

    assert TestClient(app).get("/").status_code == 404


def test_api_routes_win_over_the_frontend_mount(tmp_path, monkeypatch):
    # Same registration order as the real module: route first, mount second.
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html>rmt finder shell</html>")
    monkeypatch.setenv("RMT_FINDER_FRONTEND_DIST", str(dist))

    from api import mount_frontend

    app = FastAPI()

    @app.get("/api/ping")
    def ping():
        return {"ok": True}

    mount_frontend(app)
    client = TestClient(app)

    assert client.get("/api/ping").json() == {"ok": True}
    assert "rmt finder shell" in client.get("/").text


def test_cors_allows_frontend_dev_origin(tmp_path, monkeypatch):
    client, _ = make_client(tmp_path, monkeypatch)

    response = client.get(
        "/api/availability", headers={"Origin": "http://localhost:5173"}
    )

    assert (
        response.headers["access-control-allow-origin"] == "http://localhost:5173"
    )


def test_availability_returns_latest_good_runs_slots(tmp_path, monkeypatch):
    client, storage = make_client(tmp_path, monkeypatch)
    run_id = storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=3,
        succeeded=3,
        failed_clinics=[],
    )
    storage.insert_slots(run_id, [make_slot()])

    response = client.get("/api/availability")

    assert response.status_code == 200
    assert response.json()["slots"] == [
        {
            "clinic_name": "Test Clinic",
            "city": "victoria",
            "platform": "janeapp",
            "rmt_name": "Jane Doe",
            "service_type": "massage_therapy",
            "treatment_name": "60min Massage",
            "duration_minutes": 60,
            "start_at": "2026-07-10T09:00:00-07:00",
            "booking_url": "https://example.com/book",
        }
    ]


def test_availability_collapses_one_opening_listed_under_two_treatments(
    tmp_path, monkeypatch
):
    # Same therapist, clinic, time and duration under an "Initial" and a plain
    # treatment is one physical opening — the frontend can't tell the rows
    # apart, so the envelope should carry it once.
    client, storage = make_client(tmp_path, monkeypatch)
    run_id = storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )
    storage.insert_slots(
        run_id,
        [
            make_slot(treatment_name="Initial 60 minute RMT Session"),
            make_slot(treatment_name="60 minute RMT Session"),
        ],
    )

    body = client.get("/api/availability").json()

    assert len(body["slots"]) == 1


def test_availability_keeps_genuinely_distinct_openings(tmp_path, monkeypatch):
    # Differ by therapist, start time, or duration → not duplicates, all kept.
    client, storage = make_client(tmp_path, monkeypatch)
    run_id = storage.record_run(
        city="victoria",
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=1,
        succeeded=1,
        failed_clinics=[],
    )
    storage.insert_slots(
        run_id,
        [
            make_slot(),
            make_slot(rmt_name="Other Therapist"),
            make_slot(start_at="2026-07-10T10:00:00-07:00"),
            make_slot(duration_minutes=90),
        ],
    )

    body = client.get("/api/availability").json()

    assert len(body["slots"]) == 4


def test_api_refuses_to_start_on_a_stale_schema(tmp_path, monkeypatch):
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(tmp_path / "test.db"))
    from api import app

    with pytest.raises(SchemaOutOfDateError, match="migrate.py"):
        with TestClient(app):
            pass


def test_api_starts_on_a_migrated_schema(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    migrated_storage(str(db_path))
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    from api import app

    with TestClient(app) as client:
        assert client.get("/api/availability").status_code == 200


def test_envelope_reports_the_current_quiet_window(tmp_path, monkeypatch):
    monkeypatch.setenv("QUIET_HOURS_START", "23:00")
    monkeypatch.setenv("QUIET_HOURS_END", "06:00")
    client, _ = make_client(tmp_path, monkeypatch)
    from api import app, get_clock

    three_am = datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)
    app.dependency_overrides[get_clock] = lambda: (lambda: three_am)

    body = client.get("/api/availability").json()

    assert body["quiet_hours"] == {
        "start": "2026-10-08T23:00:00-07:00",
        "end": "2026-10-09T06:00:00-07:00",
    }


def test_envelope_quiet_hours_is_null_when_off(tmp_path, monkeypatch):
    monkeypatch.delenv("QUIET_HOURS_START", raising=False)
    monkeypatch.delenv("QUIET_HOURS_END", raising=False)
    client, _ = make_client(tmp_path, monkeypatch)

    body = client.get("/api/availability").json()

    assert body["quiet_hours"] is None


def test_api_refuses_to_start_on_bad_quiet_hours(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    migrated_storage(str(db_path))
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    monkeypatch.setenv("QUIET_HOURS_START", "23:00")
    monkeypatch.delenv("QUIET_HOURS_END", raising=False)
    from api import app

    with pytest.raises(ValueError, match="QUIET_HOURS_END"):
        with TestClient(app):
            pass


def test_api_warns_about_a_suspiciously_long_quiet_window(
    tmp_path, monkeypatch, caplog
):
    db_path = tmp_path / "test.db"
    migrated_storage(str(db_path))
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    monkeypatch.setenv("QUIET_HOURS_START", "22:00")
    monkeypatch.setenv("QUIET_HOURS_END", "20:20")
    from api import app

    with caplog.at_level(logging.WARNING), TestClient(app):
        pass

    assert "22h20m" in caplog.text
