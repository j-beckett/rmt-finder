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


def test_city_param_filters_slots_case_insensitively(tmp_path, monkeypatch):
    client, storage = make_client(tmp_path, monkeypatch)
    run_id = storage.record_run(
        started_at="2026-07-09T10:00:00+00:00",
        finished_at="2026-07-09T10:01:30+00:00",
        attempted=2,
        succeeded=2,
        failed_clinics=[],
    )
    storage.insert_slots(
        run_id, [make_slot(city="victoria"), make_slot(city="vancouver")]
    )

    body = client.get("/api/availability", params={"city": "Victoria"}).json()

    assert [slot["city"] for slot in body["slots"]] == ["victoria"]


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
