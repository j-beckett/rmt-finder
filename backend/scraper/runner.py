import time

import config

from .adapters.janeapp import JaneAppAdapter
from .clinics import CLINICS, Platform
from .models import RunResult


ADAPTERS = {
    Platform.JANEAPP: JaneAppAdapter(),
}


def run_all(city: str = None, clinics=None, adapters=None, sleep=time.sleep) -> RunResult:
    """
    Run all clinic scrapers and return per-clinic outcomes plus the
    normalized slots. Optionally filter by city.
    """
    if clinics is None:
        clinics = CLINICS
    if adapters is None:
        adapters = ADAPTERS

    if city:
        clinics = [c for c in clinics if c.city.lower() == city.lower()]

    result = RunResult(slots=[], attempted=[], succeeded=[], failed=[])

    for clinic in clinics:
        adapter = adapters.get(clinic.platform)

        if not adapter:
            print(f"No adapter found for platform: {clinic.platform}")
            continue

        # Courtesy pause between clinics (not before the first) so a run
        # never hits Jane's servers back-to-back.
        if result.attempted:
            sleep(config.inter_clinic_sleep_seconds())

        result.attempted.append(clinic.name)
        print(f"Scraping {clinic.name}...")

        try:
            clinic_results = adapter.fetch_availability(clinic)
            result.slots.extend(clinic_results)
            result.succeeded.append(clinic.name)
            print(f"  Found {len(clinic_results)} slot(s)")
        except Exception as e:
            result.failed.append(clinic.name)
            print(f"  Error scraping {clinic.name}: {e}")

    return result
