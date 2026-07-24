import os
from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from scraper.clinics import CLINICS
from storage import Storage

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.frontend_origin()],
    allow_methods=["GET"],
)


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


@app.get("/api/availability")
def availability(city: str | None = None):
    storage = Storage(config.db_path())
    good = storage.latest_good_run()
    latest = storage.latest_run()
    run, slots = good if good else (None, [])
    if city is not None:
        slots = [slot for slot in slots if slot.city.lower() == city.lower()]
    slots = _dedupe_slots(slots)
    return {
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
        "clinics_total": len(CLINICS),
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
