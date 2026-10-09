from types import SimpleNamespace

import config
from scraper.clinics import cities, clinics_in_city


def clinic(name, city):
    return SimpleNamespace(name=name, city=city)


def test_cities_are_sorted_distinct_and_lowercase():
    clinics = [
        clinic("A", "Victoria"),
        clinic("B", "vancouver"),
        clinic("C", "victoria"),
    ]

    assert cities(clinics) == ["vancouver", "victoria"]


def test_clinics_in_city_matches_case_insensitively():
    a, b, c = clinic("A", "victoria"), clinic("B", "vancouver"), clinic("C", "Victoria")

    assert clinics_in_city([a, b, c], "VICTORIA") == [a, c]
    assert clinics_in_city([a, b, c], "nowhere") == []


def test_timezone_for_city_is_case_insensitive(monkeypatch):
    monkeypatch.setattr(
        config,
        "CITY_TIMEZONES",
        {"Victoria": "America/Vancouver", "Toronto": "America/Toronto"},
    )

    assert config.timezone_for_city("toronto") == "America/Toronto"
    assert config.timezone_for_city("TORONTO") == "America/Toronto"


def test_every_roster_city_has_a_timezone_row():
    from scraper.clinics import CLINICS

    zones = {name.lower() for name in config.CITY_TIMEZONES}

    assert set(cities(CLINICS)) <= zones


def test_city_name_uses_display_name_and_falls_back_to_title_case(monkeypatch):
    monkeypatch.setattr(config, "CITY_NAMES", {"langford": "Langford & West Shore"})

    assert config.city_name("LANGFORD") == "Langford & West Shore"
    assert config.city_name("victoria") == "Victoria"
