import pytest

from scraper.adapters.janeapp import JaneAppAdapter
from scraper.clinics import jane_rmt

DISCIPLINES = [{"id": 1, "name": "Massage Therapy"}]


def kept(name):
    """Whether a plain clinic (shared excludes only) keeps this treatment."""
    treatment = {"id": 9, "discipline_id": 1, "treatment_duration": 3600, "name": name}
    service_map = JaneAppAdapter()._map_services(
        jane_rmt("Any", "any"), DISCIPLINES, [treatment]
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
