from datetime import datetime, timezone

import config
from scraper.runner import run_all
from storage import Storage


def main():
    print("Starting RMT availability scrape...")
    started_at = datetime.now(timezone.utc).isoformat()
    result = run_all(city="victoria")
    finished_at = datetime.now(timezone.utc).isoformat()

    storage = Storage(config.db_path())
    run_id = storage.record_run(
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


if __name__ == "__main__":
    main()
