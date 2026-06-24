import json
import os
from datetime import date
from scraper.scraper import run_all


def main():
    print("Starting RMT availability scrape...")
    results = run_all()

    if not results:
        print("No availability found for today.")
        return

    print(f"\nFound {len(results)} available slot(s) for today ({date.today().isoformat()}):\n")
    for r in results:
        print(f"  {r['clinic']} — {r['rmt']} ({r['status']})")
        print(f"  Book: {r['booking_url']}\n")

    os.makedirs("data", exist_ok=True)
    filename = f"data/{date.today().isoformat()}.json"
    with open(filename, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Results saved to {filename}")


if __name__ == "__main__":
    main()