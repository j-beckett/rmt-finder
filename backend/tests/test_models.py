from scraper.models import AvailabilityResult, ServiceType


def test_availability_result_holds_service_type_value():
    result = AvailabilityResult(
        clinic_name="Test Clinic",
        city="victoria",
        platform="jane",
        rmt_name="Jane Doe",
        service_type=ServiceType.MASSAGE_THERAPY,
        treatment_name="60min Massage",
        duration_minutes=60,
        start_at="2026-07-10T09:00:00",
        booking_url="https://example.com/book",
    )

    assert result.service_type.value == "massage_therapy"
