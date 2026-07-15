from dataclasses import asdict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config
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


@app.get("/api/availability")
def availability(city: str | None = None):
    storage = Storage(config.db_path())
    good = storage.latest_good_run()
    latest = storage.latest_run()
    run, slots = good if good else (None, [])
    if city is not None:
        slots = [slot for slot in slots if slot.city.lower() == city.lower()]
    return {
        "scraped_at": run.finished_at if run else None,
        "latest_attempt_at": latest.finished_at if latest else None,
        "clinics_attempted": run.clinics_attempted if run else None,
        "failed_clinics": run.failed_clinics if run else [],
        # Window metadata comes from config, not the run, so the frontend never
        # hardcodes the lookahead or the city's timezone.
        "window_days": config.lookahead_days(),
        "timezone": config.timezone_for_city(city),
        "slots": [_slot_dict(slot) for slot in slots],
    }
