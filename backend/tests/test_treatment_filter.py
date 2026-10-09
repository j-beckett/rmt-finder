import pytest

from scraper.adapters.janeapp import JaneAppAdapter
from scraper.clinics import jane_rmt

DISCIPLINES = [{"id": 1, "name": "Massage Therapy"}]


def kept(name):
    """Whether a plain clinic (shared excludes only) keeps this treatment."""
    treatment = {"id": 9, "discipline_id": 1, "treatment_duration": 3600, "name": name}
    service_map = JaneAppAdapter()._map_services(
        jane_rmt("Any", "any", slug="any"), DISCIPLINES, [treatment]
    )
    return bool(service_map)


# Real names seen on Jane (2026-10-08) that slipped past the shared list.
@pytest.mark.parametrize(
    "name",
    [
        "60 minute Buccal Massage Therapy",
        "Instrument Assisted Soft Tissue Mobilization(IASTM) 60 minute Massage Therapy",
        "Mastectomy and Breast Surgery Massage 60 minutes",
        "Therapeutic Breast Massage",
        "Therapeutic Abdominal Massage",
        "C- Section Scar Tissue Mobilization",
        "Child -Massage Therapy 60 min",
        "VA Massage Therapy: Return Visit (60 minutes)",
        "Massage Therapy Return Visit - 60 mins",
        "60 Minute Wellness Massage - Non-Registered Massage Therapy",
    ],
)
def test_shared_excludes_drop_specialty_and_non_rmt_treatments(name):
    assert not kept(name)


@pytest.mark.parametrize(
    "name",
    [
        "60 Minute Registered Massage Therapy",
        "Massage Therapy: First Visit (60 minutes)",
        "RMT Assessment ＆Treatment - 60 minutes",
    ],
)
def test_shared_excludes_keep_general_rmt_treatments(name):
    assert kept(name)


def kept_names(*treatments):
    """Treatment names a plain clinic keeps from (name, minutes) pairs."""
    raw = [
        {"id": i, "discipline_id": 1, "treatment_duration": minutes * 60, "name": name}
        for i, (name, minutes) in enumerate(treatments)
    ]
    clinic = jane_rmt("Any", "any", slug="any")
    service_map = JaneAppAdapter()._map_services(clinic, DISCIPLINES, raw)
    return [t["name"] for ts in service_map.values() for t in ts]


# Real first-visit names from clinics with no 60-minute option (2026-10-08).
def test_long_first_visit_is_kept_when_the_clinic_has_no_60_minute_option():
    assert kept_names(
        ("Initial Assessment & Massage Treatment - Adult", 75),
        ("Subsequent 60-minute appointment", 60),
        ("Subsequent 75-minute appointment", 75),
    ) == ["Initial Assessment & Massage Treatment - Adult"]


def test_long_first_visit_is_ignored_when_a_60_minute_option_exists():
    # Taking both would list each opening twice, as a 60 and as a 75.
    assert kept_names(
        ("Massage Therapy: First Visit (60 minutes)", 60),
        ("Massage Therapy: First Visit (75 minutes)", 75),
    ) == ["Massage Therapy: First Visit (60 minutes)"]


@pytest.mark.parametrize(
    "name, minutes",
    [
        ("Initial massage therapy 70 minutes", 70),
        ("Initial treatment 60 min", 75),  # named 60, booked as 75 with assessment
    ],
)
def test_first_visit_fallback_covers_70_and_75_minutes(name, minutes):
    assert kept_names((name, minutes)) == [name]


@pytest.mark.parametrize(
    "name, minutes",
    [
        ("75 Minute Massage Therapy", 75),  # longer session, not a first visit
        ("Subsequent 75-minute appointment", 75),
        ("Initial treatment 90 mins", 105),
        ("Initial Assessment & Massage Treatment - Child", 45),
    ],
)
def test_first_visit_fallback_rejects_everything_else(name, minutes):
    assert kept_names((name, minutes)) == []
