import logging
import time
from datetime import datetime, timezone

import config
import main
from quiet_hours import is_quiet, long_window_warning
from scraper.clinics import CLINICS, cities as clinic_cities
from storage import Storage

logger = logging.getLogger(__name__)


def _utc_now():
    return datetime.now(timezone.utc)


def run_once(city, scrape=main.scrape_city, quiet=None, clock=_utc_now):
    """Scrape one city. A raising scrape is logged and recorded as a failed
    run for that city — it never propagates, so one bad city can't kill the
    loop or stop the next city. Skipped entirely during the city's quiet hours.
    """
    if is_quiet(quiet, config.timezone_for_city(city), clock()):
        logger.info("Quiet hours: skipping %s", city)
        return
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        scrape(city)
    except Exception:
        logger.exception("Scrape run failed for %s", city)
        finished_at = datetime.now(timezone.utc).isoformat()
        # The raise happened before per-clinic outcomes existed, so all we
        # can record is a zero-success run — which the serving rule skips.
        Storage(config.db_path()).record_run(
            city=city,
            started_at=started_at,
            finished_at=finished_at,
            attempted=0,
            succeeded=0,
            failed_clinics=[],
        )


def run_cycle(scrape, cities, quiet=None, clock=_utc_now):
    """One pass over the cities, strictly one after another.

    Sequential on purpose: it keeps upstream concurrency at 1 (the Jane
    openings endpoint is unofficial, so being gentle matters more than speed)
    and SQLite to a single writer. A run takes a few minutes today, which fits
    the interval. When cities x run duration approaches the interval, the plan
    is per-city refresh tiers first, then capped concurrency across cities;
    see "Why sequential scraping" in
    docs/plans/storage-hardening/decisions.md.
    """
    for city in cities:
        run_once(city, scrape, quiet=quiet, clock=clock)


def run_forever(
    scrape=main.scrape_city, sleep=time.sleep, cities=None, clock=_utc_now
):
    """Scrape every city immediately on startup, then every
    SCRAPE_INTERVAL_MINUTES. `cities` defaults to the clinic roster's cities."""
    # Fail loudly at boot if a deploy forgot migrate.py, not on the first write.
    Storage(config.db_path()).require_current()
    if cities is None:
        cities = clinic_cities(CLINICS)
    # Read once so bad QUIET_HOURS_* fail at boot, not at 11 pm.
    quiet = config.quiet_hours()
    warning = long_window_warning(quiet)
    if warning:
        logger.warning(warning)
    interval_seconds = config.scrape_interval_minutes() * 60
    while True:
        run_cycle(scrape, cities, quiet=quiet, clock=clock)
        sleep(interval_seconds)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logger.info(
        "Scheduler starting: scraping every %s minute(s)",
        config.scrape_interval_minutes(),
    )
    run_forever()
