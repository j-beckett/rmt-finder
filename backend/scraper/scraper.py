import requests
from bs4 import BeautifulSoup
from datetime import date, timedelta
from .clinics import CLINICS

def build_url(subdomain, location_slug):
  return f"https://{subdomain}.janeapp.com/locations/{location_slug}/book/month"

def fetch_availability(clinic):
  url = build_url(clinic["subdomain"], clinic["location_slug"])

  response = requests.get(url)

  if response.status_code != 200:
    print(f"Failed to fetch {clinic['name']}: {response.status_code}")
    return []
  
  return parse_availability(response.text, clinic["name"])


def parse_availability(html, clinic_name):
    soup = BeautifulSoup(html, "html.parser")
    today =  (date.today() + timedelta(days=1)).isoformat() # "2026-06-21"
    results = []

    links = soup.find_all("a", href=True)

    for link in links:
        href = link["href"]
        text = link.get_text(strip=False)

        if today in href and ("Available" in text or "Limited Availability" in text):
          print("TEXT:", repr(text))
          print("HREF:", href)
          print("---")
          results.append({
              "clinic": clinic_name,
              "rmt": text.replace("Available", "").replace("Limited Availability", "").strip(),
              "status": "Limited Availability" if "Limited Availability" in text else "Available",
              "booking_url": href,
          })

    return results


def run_all():
    all_results = []

    for clinic in CLINICS:
        print(f"Scraping {clinic['name']}...")
        results = fetch_availability(clinic)
        all_results.extend(results)

    return all_results



