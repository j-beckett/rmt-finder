from types import SimpleNamespace

import pytest

from scraper.adapters.janeapp import JaneAppAdapter
from scraper.clinics import jane_rmt

# Trimmed from real Jane pages (2026-10-08): each booking page states its own
# location in `App.location_id = N`; routerOptions holds the treatments.
ROUTER = """
const routerOptions = {
  disciplines: [{"id": 1, "name": "Massage Therapy", "professional_title": "RMT"}],
  treatments: [{"id": 3, "discipline_id": 1, "treatment_duration": 3600, "name": "Massage Therapy 60 Minutes"}],
  staff_members: [{"id": 7, "professional_name": "Kari Lund"}]
}
"""


def booking_page(location_id):
    return f"App.location_id = {location_id}\n{ROUTER}"


def home_with_links(*slugs):
    return "".join(f'<a href="/locations/{slug}/book">{slug}</a>' for slug in slugs)


class FakeSession:
    """Serves canned pages by URL and records every request."""

    def __init__(self, pages, openings=()):
        self.pages = pages
        self.openings = list(openings)
        self.requested = []

    def get(self, url, headers=None):
        self.requested.append(url)
        if "/api/v2/openings/" in url:
            return SimpleNamespace(status_code=200, text="", json=lambda: self.openings)
        if url in self.pages:
            return SimpleNamespace(status_code=200, text=self.pages[url])
        return SimpleNamespace(status_code=404, text="")


BASE = "https://clinic.janeapp.com"


def test_location_id_is_read_from_the_homepage():
    session = FakeSession({BASE: booking_page(2)})

    discovered = JaneAppAdapter().discover(jane_rmt("Kari Lund", "clinic"), session)

    assert discovered["location_id"] == 2
    assert discovered["booking_url"] == BASE


def test_a_single_location_link_is_followed_when_the_homepage_has_no_id():
    session = FakeSession(
        {
            BASE: home_with_links("van-isle-wellness"),
            f"{BASE}/locations/van-isle-wellness/book": booking_page(2),
        }
    )

    discovered = JaneAppAdapter().discover(jane_rmt("Kari Lund", "clinic"), session)

    assert discovered["location_id"] == 2
    assert discovered["booking_url"] == f"{BASE}/locations/van-isle-wellness/book"


def test_a_configured_location_slug_picks_that_location():
    session = FakeSession(
        {
            BASE: home_with_links("saanichton-health-centre", "westshore"),
            f"{BASE}/locations/saanichton-health-centre/book": booking_page(1),
            f"{BASE}/locations/westshore/book": booking_page(4),
        }
    )
    clinic = jane_rmt("Natural Balance", "clinic", location="westshore")

    discovered = JaneAppAdapter().discover(clinic, session)

    assert discovered["location_id"] == 4
    assert discovered["booking_url"] == f"{BASE}/locations/westshore/book"


def test_several_locations_without_a_configured_slug_fail_loudly():
    session = FakeSession(
        {
            BASE: home_with_links("saanichton-health-centre", "westshore"),
            f"{BASE}/locations/saanichton-health-centre/book": booking_page(1),
            f"{BASE}/locations/westshore/book": booking_page(4),
        }
    )

    with pytest.raises(ValueError, match="saanichton-health-centre, westshore"):
        JaneAppAdapter().discover(jane_rmt("Natural Balance", "clinic"), session)


def test_a_configured_slug_that_does_not_exist_fails_loudly():
    session = FakeSession({BASE: home_with_links("westshore")})
    clinic = jane_rmt("Natural Balance", "clinic", location="langford")

    with pytest.raises(ValueError, match="langford"):
        JaneAppAdapter().discover(clinic, session)


def test_openings_are_requested_for_the_discovered_location(monkeypatch):
    monkeypatch.setattr(JaneAppAdapter, "_is_within_lookahead", lambda self, s: True)
    session = FakeSession(
        {BASE: booking_page(2)},
        openings=[{"start_at": "2026-10-09T10:00:00-07:00", "staff_member_id": 7}],
    )
    monkeypatch.setattr("scraper.adapters.janeapp.make_session", lambda: session)

    slots = JaneAppAdapter().fetch_availability(jane_rmt("Kari Lund", "clinic"))

    openings_calls = [u for u in session.requested if "/api/v2/openings/" in u]
    assert openings_calls and all("location_id=2&" in u for u in openings_calls)
    assert [(s.rmt_name, s.booking_url) for s in slots] == [("Kari Lund", BASE)]
