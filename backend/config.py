import os

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
CITY_TIMEZONES = {"Victoria": "America/Vancouver"}
DEFAULT_CITY = "Victoria"


def timezone_for_city(city: str | None) -> str:
    """IANA timezone for a city, falling back to the default city's zone."""
    return CITY_TIMEZONES.get(city or DEFAULT_CITY, CITY_TIMEZONES[DEFAULT_CITY])


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


def frontend_dist_path() -> str:
    """Built frontend location, overridable via RMT_FINDER_FRONTEND_DIST."""
    return os.environ.get(
        "RMT_FINDER_FRONTEND_DIST", os.path.join(_REPO_ROOT, "frontend", "dist")
    )


def frontend_origin() -> str:
    """CORS origin for the frontend, overridable via RMT_FINDER_FRONTEND_ORIGIN."""
    return os.environ.get("RMT_FINDER_FRONTEND_ORIGIN", "http://localhost:5173")
