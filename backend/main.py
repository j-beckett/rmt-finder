from datetime import datetime, timezone

import config
from scraper.clinics import CLINICS, cities
from scraper.runner import run_all
from storage import Storage


def scrape_city(city: str):
    """Scrape one city and record its run. The scheduler calls this once per
    city per cycle."""
    print(f"Starting RMT availability scrape for {city}...")
    started_at = datetime.now(timezone.utc).isoformat()
    result = run_all(city=city)
    finished_at = datetime.now(timezone.utc).isoformat()

    storage = Storage(config.db_path())
    run_id = storage.record_run(
        city=city,
        started_at=started_at,
        finished_at=finished_at,
        attempted=len(result.attempted),
        succeeded=len(result.succeeded),
        failed_clinics=result.failed,
    )
    storage.insert_slots(run_id, result.slots)

    print(
        f"\nRun {run_id}: {len(result.attempted)} clinics attempted,"
        f" {len(result.succeeded)} succeeded, {len(result.failed)} failed"
    )
    if result.failed:
        print(f"Failed clinics: {', '.join(result.failed)}")
    print(f"{len(result.slots)} slot(s) recorded")

    # Prune only on the back of a good scrape: a failing scraper must never
    # be what deletes data. (prune_slots also always keeps each city's latest
    # good run, the API's fallback.)
    if result.succeeded:
        retention_days = config.retention_days()
        pruned = storage.prune_slots(city, retention_days)
        if pruned:
            print(f"Pruned {pruned} slot(s) older than {retention_days} day(s)")


def main():
    """Scrape every city in the roster, one after another (local CLI)."""
    for city in cities(CLINICS):
        scrape_city(city)


def cli():
    """Local entry point. Migrates first so `python main.py` works on a fresh
    checkout; main() itself never migrates because the scheduler calls it every
    cycle and the deploy (migrate.py) owns schema changes in production."""
    Storage(config.db_path()).migrate()
    main()


if __name__ == "__main__":
    cli()
