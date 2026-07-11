import logging
import time
from datetime import datetime, timezone

import config
import main
from storage import Storage

logger = logging.getLogger(__name__)


def run_once(scrape=main.main):
    """One scrape cycle. A raising scrape is logged and recorded as a
    failed run — it never propagates, so one bad run can't kill the loop."""
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        scrape()
    except Exception:
        logger.exception("Scrape run failed")
        finished_at = datetime.now(timezone.utc).isoformat()
        # The raise happened before per-clinic outcomes existed, so all we
        # can record is a zero-success run — which the serving rule skips.
        Storage(config.db_path()).record_run(
            started_at=started_at,
            finished_at=finished_at,
            attempted=0,
            succeeded=0,
            failed_clinics=[],
        )


def run_forever(scrape=main.main, sleep=time.sleep):
    """Scrape immediately on startup, then every SCRAPE_INTERVAL_MINUTES."""
    interval_seconds = config.scrape_interval_minutes() * 60
    while True:
        run_once(scrape)
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
