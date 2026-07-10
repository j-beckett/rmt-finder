import main as main_module
from scraper.models import AvailabilityResult, RunResult, ServiceType
from storage import Storage


def make_slot():
    return AvailabilityResult(
        clinic_name="Good Clinic",
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
    fake_result = RunResult(
        slots=[make_slot()],
        attempted=["Good Clinic", "Broken Clinic"],
        succeeded=["Good Clinic"],
        failed=["Broken Clinic"],
    )
    monkeypatch.setattr(main_module, "run_all", lambda city=None: fake_result)

    main_module.main()

    run, slots = Storage(str(db_path)).latest_good_run()
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
