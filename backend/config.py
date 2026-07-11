import os

# Global scraper settings
# Any other settings that are global — like a default city, or a request timeout — live here too.
LOOKAHEAD_HOURS = 24

# Anchored to the repo root so the CLI, scheduler, and API all resolve the
# same file no matter which directory they are launched from.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DB_PATH = os.path.join(_REPO_ROOT, "data", "rmt-finder.db")


def db_path() -> str:
    """Database location, overridable via RMT_FINDER_DB_PATH."""
    return os.environ.get("RMT_FINDER_DB_PATH", DEFAULT_DB_PATH)


def scrape_interval_minutes() -> int:
    """Minutes between scheduled scrapes, overridable via SCRAPE_INTERVAL_MINUTES."""
    return int(os.environ.get("SCRAPE_INTERVAL_MINUTES", "15"))


def frontend_origin() -> str:
    """CORS origin for the frontend, overridable via RMT_FINDER_FRONTEND_ORIGIN."""
    return os.environ.get("RMT_FINDER_FRONTEND_ORIGIN", "http://localhost:5173")
