import os
import zoneinfo
from datetime import time
from typing import NamedTuple

# Global scraper settings
# Any other settings that are global — like a default city, or a request timeout — live here too.

# Anchored to the repo root so the CLI, scheduler, and API all resolve the
# same file no matter which directory they are launched from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(_REPO_ROOT, "data", "rmt-finder.db")


def db_path() -> str:
    """Database location, overridable via RMT_FINDER_DB_PATH."""
    return os.environ.get("RMT_FINDER_DB_PATH", DEFAULT_DB_PATH)


# City → IANA timezone. Slot start times carry a fixed UTC offset, but working
# out which calendar day a slot falls on (for the Today/Tomorrow filter) needs
# the city's zone so PST/PDT is handled correctly. Add a row per new city.
CITY_TIMEZONES = {"Victoria": "America/Vancouver", "Langford": "America/Vancouver"}
DEFAULT_CITY = "Victoria"

# Use only the pinned tzdata package, never host tz data, so every machine
# agrees on rule changes (e.g. BC's permanent UTC-7 from 2026-11-01).
zoneinfo.reset_tzpath(to=[])


# Display names where the city key alone isn't enough; others are title-cased.
CITY_NAMES = {"langford": "Langford & West Shore"}


def city_name(city: str) -> str:
    return CITY_NAMES.get(city.lower(), city.title())


def timezone_for_city(city: str | None) -> str:
    """IANA timezone for a city, falling back to the default city's zone."""
    zones = {name.lower(): zone for name, zone in CITY_TIMEZONES.items()}
    return zones.get((city or DEFAULT_CITY).lower(), zones[DEFAULT_CITY.lower()])


def lookahead_days() -> int:
    """Whole calendar days of availability to collect and show, via LOOKAHEAD_DAYS.

    Whole days (not rolling hours) so "the next three days" is exactly what the
    scraper collects and the frontend shows — no partial trailing day that the
    day filter can't reach. 3 is provisional; watch slot volume for a few days.
    """
    return int(os.environ.get("LOOKAHEAD_DAYS", "3"))


def inter_clinic_sleep_seconds() -> float:
    """Courtesy pause between clinic scrapes, via INTER_CLINIC_SLEEP_SECONDS.

    Spaces requests out so a full run never hits Jane's servers
    back-to-back; 23 clinics at 1.5s adds ~35s to a run, which is nothing
    against a 15-minute interval.
    """
    return float(os.environ.get("INTER_CLINIC_SLEEP_SECONDS", "1.5"))


def scrape_interval_minutes() -> int:
    """Minutes between scheduled scrapes, overridable via SCRAPE_INTERVAL_MINUTES."""
    return int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "15"))


def retention_days() -> int:
    """Days of slot history to keep, via RETENTION_DAYS; 0 keeps everything.

    Measured by when a run finished, not when its slots start. Only slots are
    pruned (scrape_runs is the health history and is kept), and each city's
    latest good run survives regardless, since the API falls back to it.
    """
    return int(os.environ.get("RETENTION_DAYS", "7"))


def _parse_hh_mm(name: str, value: str) -> time:
    """A 24-hour "HH:MM" setting, or a ValueError naming the setting."""
    try:
        hours, _, minutes = value.partition(":")
        if not (len(hours) == len(minutes) == 2 and (hours + minutes).isdigit()):
            raise ValueError
        return time(int(hours), int(minutes))
    except ValueError:
        raise ValueError(
            f"{name} must be a 24-hour time as HH:MM (e.g. 23:00), got {value!r}."
        ) from None


class QuietHours(NamedTuple):
    start: time
    end: time


def quiet_hours() -> QuietHours | None:
    """QUIET_HOURS_START/END as city-local HH:MM, or None (off) when both unset.

    Half-set, malformed, or equal times raise, so a typo fails at startup.
    """
    start = os.environ.get("QUIET_HOURS_START")
    end = os.environ.get("QUIET_HOURS_END")
    if not start and not end:
        return None
    if not start or not end:
        missing = "QUIET_HOURS_END" if start else "QUIET_HOURS_START"
        raise ValueError(
            f"Quiet hours need both times; {missing} is not set."
            " Set both QUIET_HOURS_START and QUIET_HOURS_END, or neither."
        )
    window = QuietHours(
        _parse_hh_mm("QUIET_HOURS_START", start), _parse_hh_mm("QUIET_HOURS_END", end)
    )
    if window.start == window.end:
        raise ValueError(
            f"QUIET_HOURS_START and QUIET_HOURS_END are both {start}, which is"
            " ambiguous. To turn quiet hours off, leave both unset."
        )
    return window


def frontend_dist_path() -> str:
    """Built frontend location, overridable via RMT_FINDER_FRONTEND_DIST."""
    return os.environ.get(
        "RMT_FINDER_FRONTEND_DIST", os.path.join(_REPO_ROOT, "frontend", "dist")
    )


def frontend_origin() -> str:
    """CORS origin for the frontend, overridable via RMT_FINDER_FRONTEND_ORIGIN."""
    return os.environ.get("RMT_FINDER_FRONTEND_ORIGIN", "http://localhost:5173")
