import re
import json
import html
from datetime import datetime, timedelta, timezone
from .base import BaseAdapter
from ..models import AvailabilityResult, ServiceType
from ..web_client import make_session
from config import LOOKAHEAD_HOURS


SERVICE_TYPE_KEYWORDS = {
    ServiceType.MASSAGE_THERAPY: ["rmt", "massage therapist", "massage therapy"],
    ServiceType.ACUPUNCTURE: ["acupuncturist", "r. ac", "registered acupuncturist"],
    ServiceType.PHYSIOTHERAPY: ["physiotherapist", "physiotherapy"],
}


class JaneAppAdapter(BaseAdapter):
    def _extract_js_object(self, text: str, start_pattern: str) -> str | None:
        """Extract a JS object literal by counting braces, handling quoted strings."""
        start_match = re.search(start_pattern, text)
        if not start_match:
            return None

        start = start_match.end() - 1
        depth = 0
        in_string = False
        escape_next = False

        for i, ch in enumerate(text[start:], start):
            if escape_next:
                escape_next = False
                continue
            if ch == "\\" and in_string:
                escape_next = True
                continue
            if ch == '"':
                in_string = not in_string
                continue
            if not in_string:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start : i + 1]

        return None

    def _fetch_router_options(self, clinic) -> dict:
        url = f"https://{clinic.subdomain}.janeapp.com"

        # Create a session and store it so _fetch_openings can reuse it
        # Jane sets cookies on the homepage that the API requires
        self._session = make_session()
        response = self._session.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch {clinic.name}: {response.status_code}")
            return {}

        # Count curly braces to extract the complete routerOptions object
        raw = self._extract_js_object(response.text, r"const routerOptions\s*=\s*\{")

        if not raw:
            print(f"Could not find routerOptions for {clinic.name}")
            return {}

        try:
            decoded = html.unescape(raw)
            # Only quote top-level unquoted keys at start of lines, not content inside strings
            fixed = re.sub(
                r"^\s*([a-zA-Z_$][a-zA-Z0-9_$]*)\s*:",
                r'"\1":',
                decoded,
                flags=re.MULTILINE,
            )
            # Remove trailing commas
            fixed = re.sub(r",(\s*[}\]])", r"\1", fixed)
            return json.loads(fixed)
        except json.JSONDecodeError as e:
            print(f"Could not parse routerOptions for {clinic.name}: {e}")
            print("Raw (first 500 chars):", raw[:500])
            return {}

    def _build_staff_lookup(self, staff_members: list) -> dict:
        """Build a staff_id -> name dictionary."""
        return {s["id"]: s["professional_name"] for s in staff_members}

    def _map_services(self, clinic, disciplines: list, treatments: list) -> dict:
        service_map = {}

        for service in clinic.services:
            service_type = service["type"]
            durations = service["durations"]
            keywords = SERVICE_TYPE_KEYWORDS.get(service_type, [])
            discipline_names = service.get("discipline_names", [])
            exclude_keywords = service.get("exclude_treatment_keywords", [])

            matching_discipline_ids = [
                d["id"]
                for d in disciplines
                if (
                    any(
                        name.lower() in d.get("name", "").lower()
                        for name in discipline_names
                    )
                    if discipline_names
                    else any(
                        keyword in d.get("professional_title", "").lower()
                        for keyword in keywords
                    )
                )
            ]

            matching_treatments = [
                {
                    "treatment_id": t["id"],
                    "discipline_id": t["discipline_id"],
                    "duration_minutes": t["treatment_duration"] // 60,
                }
                for t in treatments
                if t["discipline_id"] in matching_discipline_ids
                and t["treatment_duration"] // 60 in durations
                and not any(kw in t.get("name", "").lower() for kw in exclude_keywords)
            ]

            for t in treatments:
                if (
                    t["discipline_id"] in matching_discipline_ids
                    and t["treatment_duration"] // 60 in durations
                    and not any(
                        kw in t.get("name", "").lower() for kw in exclude_keywords
                    )
                ):
                    print(
                        f"    Matched treatment: [{t['id']}] {t['name']} (discipline_id={t['discipline_id']})"
                    )

            if matching_treatments:
                service_map[service_type] = matching_treatments

        return service_map

    def _is_within_lookahead(self, start_at: str) -> bool:
        """Check if a slot falls within the next LOOKAHEAD_HOURS hours."""
        try:
            slot_time = datetime.fromisoformat(start_at)
            now = datetime.now(timezone.utc).astimezone(slot_time.tzinfo)
            cutoff = now + timedelta(hours=LOOKAHEAD_HOURS)
            return now <= slot_time <= cutoff
        except ValueError:
            return False

    def _fetch_openings(
        self, clinic, service_type, treatment, staff_lookup
    ) -> list[AvailabilityResult]:
        """Query the Jane openings API for a single treatment and return results."""
        url = (
            f"https://{clinic.subdomain}.janeapp.com"
            f"/api/v2/openings/for_discipline"
            f"?location_id=1"
            f"&discipline_id={treatment['discipline_id']}"
            f"&treatment_id={treatment['treatment_id']}"
            f"&num_days=2"
        )

        # Reuse the session from _fetch_router_options so cookies are preserved
        response = self._session.get(
            url, headers={"Referer": f"https://{clinic.subdomain}.janeapp.com"}
        )

        if response.status_code != 200:
            print(
                f"    Openings API {response.status_code} for treatment {treatment['treatment_id']}"
            )
            return []

        openings = response.json()
        if openings:
            print(
                f"    treatment {treatment['treatment_id']}: {len(openings)} openings, first start_at={openings[0].get('start_at')}"
            )

        results = []

        for opening in openings:
            start_at = opening.get("start_at", "")

            if not self._is_within_lookahead(start_at):
                continue

            staff_id = opening.get("staff_member_id")

            results.append(
                AvailabilityResult(
                    clinic_name=clinic.name,
                    city=clinic.city,
                    platform="janeapp",
                    rmt_name=staff_lookup.get(staff_id, "Unknown"),
                    service_type=service_type,
                    duration_minutes=treatment["duration_minutes"],
                    start_at=start_at,
                    booking_url=f"https://{clinic.subdomain}.janeapp.com",
                )
            )

        return results

    def discover(self, clinic) -> dict:
        """Discover Jane-specific IDs needed to query availability."""
        router = self._fetch_router_options(clinic)

        if not router:
            return {}

        disciplines = router.get("disciplines", [])
        treatments = router.get("treatments", [])
        print(
            f"  Disciplines ({len(disciplines)}): {[d.get('professional_title') for d in disciplines]}\n"
        )
        print(
            f"  Treatments ({len(treatments)}): first 3 = {[(t.get('name'), t.get('treatment_duration')) for t in treatments[:3]]}\n"
        )

        service_map = self._map_services(clinic, disciplines, treatments)
        print(f"  Service map: {service_map}\n")

        return {
            "service_map": service_map,
            "staff_lookup": self._build_staff_lookup(router.get("staff_members", [])),
        }

    def fetch_availability(self, clinic) -> list[AvailabilityResult]:
        """Fetch all available slots for a clinic within the lookahead window."""
        discovered = self.discover(clinic)

        if not discovered:
            return []

        results = []

        for service_type, treatments in discovered["service_map"].items():
            for treatment in treatments:
                results.extend(
                    self._fetch_openings(
                        clinic,
                        service_type,
                        treatment,
                        discovered["staff_lookup"],
                    )
                )

        return results
