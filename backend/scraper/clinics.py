from dataclasses import dataclass
from enum import Enum
from .models import ServiceType


class Platform(Enum):
    JANEAPP = "janeapp"
    MINDBODY = "mindbody"


@dataclass
class ClinicConfig:
    name: str
    city: str
    platform: Platform
    services: list[dict]


@dataclass
class JaneAppConfig(ClinicConfig):
    subdomain: str = ""


@dataclass
class MindbodyConfig(ClinicConfig):
    studio_id: str = ""


DEFAULT_DURATIONS = [60]
DEFAULT_DISCIPLINE_NAMES = ["Massage Therapy"]
EXCLUDED_TREATMENT_KEYWORDS = [
    "prenatal",
    "pregnancy",
    "natal",
    "craniosacral",
    "tmj",
    "lymphatic",
    "mobile",
    "icbc",
    "wsbc",
    "hot stone",
    "facial",
    "fitness",
    "rehab",
    "sport",
    "relaxation",
    "deep tissue",
    "head",
    "foot",
    "cupping",
    "reiki",
    "follow-up",
    "follow up",
    "subsequent",
    "returning",
    "osteopathic",
    "abhyanga",
    "ayurveda",
    "tui na",
    "detox",
    "face",
    "therapeutic exercise",
    "stretch therapy",
]


def jane_rmt(
    name: str,
    subdomain: str,
    city: str = "victoria",
    discipline_names: list[str] = None,
    extra_excludes: list[str] = None,
) -> JaneAppConfig:
    """Build a Jane massage-therapy clinic config.

    Most clinics use the defaults. `discipline_names` overrides which Jane
    discipline(s) count as massage therapy (e.g. a clinic that names its
    discipline just "Massage" instead of "Massage Therapy"). `extra_excludes`
    adds clinic-specific treatment-name exclusions on top of the shared list
    (e.g. "non-registered" for a clinic that mixes RMT and non-RMT massage).
    """
    return JaneAppConfig(
        name=name,
        city=city,
        platform=Platform.JANEAPP,
        subdomain=subdomain,
        services=[
            {
                "type": ServiceType.MASSAGE_THERAPY,
                "durations": DEFAULT_DURATIONS,
                "discipline_names": discipline_names or DEFAULT_DISCIPLINE_NAMES,
                "exclude_treatment_keywords": (
                    EXCLUDED_TREATMENT_KEYWORDS + (extra_excludes or [])
                ),
            }
        ],
    )


CLINICS = [
    # Working
    jane_rmt("Geometry", "geometry"),
    jane_rmt("ViVi Therapy", "vivitherapy"),
    jane_rmt("Remedy Wellness Centre", "remedywellnesscentre"),
    jane_rmt("Saanich Massage", "saanichmassage"),
    jane_rmt("Joseph Fisher RMT", "jfrmt"),
    jane_rmt("Massage Therapy Clinic", "massagetherapyclinic"),
    jane_rmt("Downtown Victoria Massage", "downtownvictoriamassagetherapy"),
    jane_rmt("Victoria Clayton RMT", "victoriaclaytonrmt"),
    # New to test
    jane_rmt("Synergy Massage", "synergymassage"),
    jane_rmt("The Lab Victoria", "labvictoria"),
    jane_rmt("Active Health Clinic", "activehealthclinic"),
    jane_rmt("Reach Health", "reachhealth"),
    jane_rmt("Renew Health", "renew"),
    jane_rmt("A Balanced Body", "abalancedbody"),
    jane_rmt("Vitality Treatment Centre", "vitalitytreatment"),
    # Testing the /locations/ fallback
    jane_rmt("Tall Tree Health", "talltreehealthjamesbay"),
    jane_rmt("Massage Therapy Group", "massagetherapygroup"),
    jane_rmt("Equilibrium Massage Therapy", "equilibriummassagetherapy"),
    jane_rmt("Victoria Massage Therapy", "victoriamassagetherapy"),
    # Added 2026-07-09 after web search + location verification
    jane_rmt("Infinity Massage and Acupuncture", "infinitymassage"),
    jane_rmt("Optimal Health Massage Therapy", "optimalhealthmassage"),
    jane_rmt("Glow Integrative Clinic", "glowintegrative"),
    jane_rmt("Heart of the Village Massage Therapy", "heartofthevillagemassagetherapy"),
    # Added 2026-07-23 after web search + location verification
    jane_rmt("Atlas Health Therapy", "atlashealththerapy"),
    jane_rmt("Discovery Health", "discoveryhealth"),
    jane_rmt("Wild Cove Massage Therapy", "wildcovemassagetherapy"),
    # Acupuncture-heavy clinic that also lists specialized "Breast Massage"
    # treatments under massage therapy; keep those out of general RMT results.
    jane_rmt("Pearl Healthcare", "pearlhealthcare", extra_excludes=["breast"]),
    # Names its discipline just "Massage" (not "Massage Therapy") and sells
    # non-RMT massage under it, so it needs a per-clinic override.
    jane_rmt(
        "Victoria Centre Acupuncture and Massage",
        "vcaspa",
        discipline_names=["Massage"],
        extra_excludes=["non-registered", "certified massage"],
    ),
    # Needs investigation
    # jane_rmt("Solace Massage", "solacemassagevictoria"), dupes
    # Deliberately excluded — WCCMT public intern clinic. Treatments are
    # provided by student interns supervised by RMT instructors, not by RMTs
    # themselves, so it doesn't fit an "RMT availability" tool.
    # jane_rmt("WCCMT Victoria Intern Clinic", "victoriacollegeofmassage"),
    # Deliberately excluded — not a walk-in clinic, so results wouldn't be
    # useful even if scraped correctly. Only treatments are mobile/hotel
    # visits (e.g. "60min HOTEL RMT Massage", "...at a Partnered Location").
    # Revisit if we ever want to support mobile/in-home appointments.
    # jane_rmt("Compass Massage", "compassmassage"),
]
