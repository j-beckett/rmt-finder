import re
import json
import html
from datetime import datetime, time, timedelta, timezone
from .base import BaseAdapter
from ..models import AvailabilityResult, ServiceType
from ..web_client import make_session
from config import lookahead_days


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

    def _fetch_router_options(self, clinic, session) -> dict:
        url = f"https://{clinic.subdomain}.janeapp.com"

        # Jane sets cookies on the homepage that the openings API requires,
        # so the same session must be used for every request to this clinic
        response = session.get(url)

        if response.status_code != 200:
            print(f"Failed to fetch {clinic.name}: {response.status_code}")
            return {}

        # Count curly braces to extract the complete routerOptions object
        raw = self._extract_js_object(response.text, r"const routerOptions\s*=\s*\{")

        if not raw:
            # Some clinics only embed routerOptions on a location booking page
            location_paths = re.findall(
                r'href="(/locations/[^#"]+/book)"', response.text
            )
            unique_paths = list(dict.fromkeys(location_paths))

            for path in unique_paths[:3]:
                location_url = f"https://{clinic.subdomain}.janeapp.com{path}"
                print(f"  Trying location path: {location_url}")
                location_response = session.get(location_url)

                if location_response.status_code != 200:
                    continue

                raw = self._extract_js_object(
                    location_response.text, r"const routerOptions\s*=\s*\{"
                )

                if raw:
                    break

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
        """Build a staff_id -> name dictionary.

        Jane double-HTML-escapes the JSON embedded in its page, so the single
        unescape in _fetch_router_options only peels the outer layer and leaves
        entities behind in string values (e.g. 'Joseph &quot;Stephane&quot;
        Gaudet'). Unescape the name here, after JSON parsing, where turning
        &quot; back into " is safe and can't break the surrounding structure.
        """
        return {
            s["id"]: html.unescape(s["professional_name"]) for s in staff_members
        }

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
                    # Same double-escaping as staff names (see _build_staff_lookup).
                    "name": html.unescape(t["name"]),
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

    def _is_within_lookahead(self, start_at: str, now: datetime | None = None) -> bool:
        """Check if a slot falls within the next lookahead_days() calendar days.

        Floored to the clinic-local end of the last day, so the window is always
        whole days (today through today + N-1), never a ragged partial day.
        `now` is injectable for tests; it defaults to the current instant.
        """
        try:
            slot_time = datetime.fromisoformat(start_at)
            if now is None:
                now = datetime.now(timezone.utc)
            now = now.astimezone(slot_time.tzinfo)
            last_day = (now + timedelta(days=lookahead_days() - 1)).date()
            cutoff = datetime.combine(last_day, time.max, tzinfo=slot_time.tzinfo)
            return now <= slot_time <= cutoff
        except ValueError:
            return False

    def _fetch_openings(
        self, clinic, service_type, treatment, staff_lookup, session
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

        # TODO: openings API has been observed returning an empty list on some
        # requests for a treatment that has openings moments later (e.g.
        # Equilibrium Massage Therapy). Look into whether this is rate
        # limiting, caching, or something else before adding a retry.
        response = session.get(
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
                    treatment_name=treatment["name"],
                    duration_minutes=treatment["duration_minutes"],
                    start_at=start_at,
                    booking_url=f"https://{clinic.subdomain}.janeapp.com",
                )
            )

        return results

    def discover(self, clinic, session) -> dict:
        """Discover Jane-specific IDs needed to query availability."""
        router = self._fetch_router_options(clinic, session)

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
        # One session per clinic scrape: Jane's cookies are per subdomain,
        # and keeping the session out of adapter state keeps the adapter
        # safe to share across clinics (and threads, if we ever parallelize)
        session = make_session()
        discovered = self.discover(clinic, session)

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
                        session,
                    )
                )

        return results
