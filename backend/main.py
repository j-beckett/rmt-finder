import json
import os
from datetime import datetime, timezone
from scraper.runner import run_all
from scraper.models import ServiceType


def main():
    print("Starting RMT availability scrape...")
    results = run_all(city="victoria")

    if not results:
        print("No availability found in the next 24 hours.")
        return

    print(f"\nFound {len(results)} slot(s) in the next 24 hours:\n")

    for r in results:
        print(f"  {r.clinic_name} — {r.rmt_name}")
        print(f"  {r.treatment_name} | {r.duration_minutes} min | {r.start_at}")
        print(f"  Book: {r.booking_url}\n")

    os.makedirs("data", exist_ok=True)
    filename = f"data/{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S')}.json"

    with open(filename, "w") as f:
        json.dump(
            [
                {
                    "clinic": r.clinic_name,
                    "city": r.city,
                    "platform": r.platform,
                    "rmt": r.rmt_name,
                    "service": r.service_type.value,
                    "treatment_name": r.treatment_name,
                    "duration_minutes": r.duration_minutes,
                    "start_at": r.start_at,
                    "booking_url": r.booking_url,
                }
                for r in results
            ],
            f,
            indent=2,
        )

    print(f"Results saved to {filename}")


if __name__ == "__main__":
    main()