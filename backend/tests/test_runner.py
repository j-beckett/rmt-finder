from scraper.clinics import Platform, jane_rmt
from scraper.models import AvailabilityResult, ServiceType
from scraper.runner import run_all


def make_slot(clinic_name):
    return AvailabilityResult(
        clinic_name=clinic_name,
        city="victoria",
        platform="janeapp",
        rmt_name="Jane Doe",
        service_type=ServiceType.MASSAGE_THERAPY,
        treatment_name="60min Massage",
        duration_minutes=60,
        start_at="2026-07-10T09:00:00-07:00",
        booking_url="https://example.com/book",
    )


class StubAdapter:
    def fetch_availability(self, clinic):
        if clinic.name == "Broken Clinic":
            raise RuntimeError("boom")
        return [make_slot(clinic.name)]


def test_run_all_reports_per_clinic_outcomes_alongside_slots():
    clinics = [
        jane_rmt("Good Clinic", "goodclinic"),
        jane_rmt("Broken Clinic", "brokenclinic"),
    ]

    result = run_all(clinics=clinics, adapters={Platform.JANEAPP: StubAdapter()})

    assert result.attempted == ["Good Clinic", "Broken Clinic"]
    assert result.succeeded == ["Good Clinic"]
    assert result.failed == ["Broken Clinic"]
    assert result.slots == [make_slot("Good Clinic")]
