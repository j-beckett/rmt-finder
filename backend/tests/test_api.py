from fastapi.testclient import TestClient

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


def make_client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("RMT_FINDER_DB_PATH", str(db_path))
    storage = Storage(str(db_path))

    from api import app

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
