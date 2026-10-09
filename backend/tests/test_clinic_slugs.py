import re

from scraper.clinics import CLINICS

SLUG_FORMAT = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def test_every_clinic_has_a_slug():
    assert [c.name for c in CLINICS if not getattr(c, "slug", "")] == []


def test_slugs_are_lowercase_letters_digits_and_hyphens():
    assert [c.slug for c in CLINICS if not SLUG_FORMAT.match(c.slug)] == []


def test_slugs_are_unique_across_all_cities():
    slugs = [c.slug for c in CLINICS]
    assert sorted({s for s in slugs if slugs.count(s) > 1}) == []


def test_equilibrium_locations_share_a_prefix():
    equilibrium = [c for c in CLINICS if c.name.startswith("Equilibrium")]
    assert len(equilibrium) > 1
    assert all(c.slug.startswith("equilibrium-") for c in equilibrium)
