import logging
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from quiet_hours import last_window, long_window_warning
from scraper.clinics import CLINICS, cities, clinics_in_city
from storage import Storage

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Refuse to start on a stale schema or bad QUIET_HOURS_*. The deploy
    runs migrate.py before restarting; this catches a forgotten one."""
    get_storage().require_current()
    warning = long_window_warning(config.quiet_hours())
    if warning:
        logger.warning(warning)
    yield


app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.frontend_origin()],
    allow_methods=["GET"],
)


def get_storage() -> Storage:
    """FastAPI dependency. Reads the path per call so config (and tests) can
    point at a different database; construction is cheap."""
    return Storage(config.db_path())


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_clock():
    """FastAPI dependency: the current time, overridable in tests."""
    return _utc_now


def _quiet_hours_dict(city: str, now: datetime) -> dict | None:
    """Latest quiet window, so the frontend can tell a pause from a failure."""
    window = last_window(config.quiet_hours(), config.timezone_for_city(city), now)
    if window is None:
        return None
    return {"start": window.start.isoformat(), "end": window.end.isoformat()}


def _slot_dict(slot) -> dict:
    data = asdict(slot)
    data["service_type"] = slot.service_type.value
    return data


def _dedupe_slots(slots: list) -> list:
    """Collapse slots that are the same physical opening surfaced twice.

    Some Jane clinics list one appointment under two treatment products (e.g.
    an "Initial 60 minute RMT Session" and a plain "60 minute RMT Session"),
    both of which match our massage filter and both of which the openings API
    returns at the same time for the same therapist. The frontend shows only
    the therapist name and duration, and every slot links to the same clinic
    booking page, so the extra row is a visible duplicate with nothing to tell
    it apart. Collapse on (clinic, therapist, start time, duration), keeping the
    first occurrence so order is preserved. Raw slots stay in the database
    untouched, so a clinic double-listing a treatment is still visible there.
    """
    seen = set()
    unique = []
    for slot in slots:
        key = (
            slot.clinic_name,
            slot.rmt_name,
            slot.start_at,
            slot.duration_minutes,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(slot)
    return unique


@app.get("/api/cities")
def list_cities():
    return [{"slug": city, "name": config.city_name(city)} for city in cities(CLINICS)]


@app.get("/api/availability")
def availability(
    city: str | None = None,
    storage: Storage = Depends(get_storage),
    clock=Depends(get_clock),
):
    city = (city or config.DEFAULT_CITY).lower()
    if city not in cities(CLINICS):
        raise HTTPException(status_code=404, detail=f"Unknown city: {city}")
    good = storage.latest_good_run(city)
    latest = storage.latest_run(city)
    run, slots = good if good else (None, [])
    slots = _dedupe_slots(slots)
    return {
        "city": city,
        "city_name": config.city_name(city),
        "scraped_at": run.finished_at if run else None,
        "latest_attempt_at": latest.finished_at if latest else None,
        "clinics_attempted": run.clinics_attempted if run else None,
        "failed_clinics": run.failed_clinics if run else [],
        # Window metadata comes from config, not the run, so the frontend never
        # hardcodes the lookahead or the city's timezone.
        "window_days": config.lookahead_days(),
        "timezone": config.timezone_for_city(city),
        # From the clinic roster (not the run) so the frontend's about line is
        # right even before the first scrape and tracks clinics.py additions.
        "clinics_total": len(clinics_in_city(CLINICS, city)),
        "quiet_hours": _quiet_hours_dict(city, clock()),
        "slots": [_slot_dict(slot) for slot in slots],
    }


def mount_frontend(app: FastAPI) -> None:
    """Serve the built frontend (frontend/dist) from the same origin as the
    API, so one uvicorn process serves the whole site in production and the
    browser's /api fetches need no CORS. Skipped when no build exists — dev
    machines use Vite's dev server instead. Must be called after the /api
    routes are defined so they win over the "/" mount."""
    dist = config.frontend_dist_path()
    if os.path.isdir(dist):
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")


mount_frontend(app)
