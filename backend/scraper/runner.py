from .adapters.janeapp import JaneAppAdapter
from .clinics import CLINICS, Platform
from .models import AvailabilityResult


ADAPTERS = {
    Platform.JANEAPP: JaneAppAdapter(),
}


def run_all(city: str = None) -> list[AvailabilityResult]:
    """
    Run all clinic scrapers and return normalized results.
    Optionally filter by city.
    """
    clinics = CLINICS

    if city:
        clinics = [c for c in CLINICS if c.city.lower() == city.lower()]

    results = []

    for clinic in clinics:
        adapter = ADAPTERS.get(clinic.platform)

        if not adapter:
            print(f"No adapter found for platform: {clinic.platform}")
            continue

        print(f"Scraping {clinic.name}...")

        try:
            clinic_results = adapter.fetch_availability(clinic)
            results.extend(clinic_results)
            print(f"  Found {len(clinic_results)} slot(s)")
        except Exception as e:
            print(f"  Error scraping {clinic.name}: {e}")
            continue

    return results