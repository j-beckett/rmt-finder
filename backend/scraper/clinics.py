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
    # Slug from the clinic's /locations/<slug> booking link; only needed when
    # the Jane account has several locations.
    location: str = ""


@dataclass
class MindbodyConfig(ClinicConfig):
    studio_id: str = ""


DEFAULT_DURATIONS = [60]
# Fallback for clinics with no 60-minute option a new patient can book: their
# first visit is a 60-minute massage plus an assessment, booked as 70-75 min.
# Only used when nothing at DEFAULT_DURATIONS matches, so the same opening is
# never listed under both a 60 and a 75.
FIRST_VISIT_DURATIONS = [70, 75]
FIRST_VISIT_KEYWORDS = ["initial", "first visit", "new patient"]
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
    "buccal",
    "instrument assisted",
    "mastectomy",
    "breast",
    "abdominal",
    "c-section",
    "c- section",
    "child",
    "return visit",
    "va massage",
    "non-registered",
    "certified massage",
]


def cities(clinics) -> list[str]:
    """Sorted distinct lowercase cities. The scheduler scrapes these and the
    API validates ?city= against them, so the roster is the one source of
    truth: adding a clinic in a new city is all it takes to add the city."""
    return sorted({clinic.city.lower() for clinic in clinics})


def clinics_in_city(clinics, city: str) -> list:
    return [clinic for clinic in clinics if clinic.city.lower() == city.lower()]


def jane_rmt(
    name: str,
    subdomain: str,
    city: str = "victoria",
    discipline_names: list[str] = None,
    extra_excludes: list[str] = None,
    location: str = "",
) -> JaneAppConfig:
    """Build a Jane massage-therapy clinic config.

    Most clinics use the defaults. `discipline_names` overrides which Jane
    discipline(s) count as massage therapy (e.g. a clinic that names its
    discipline just "Massage" instead of "Massage Therapy"). `extra_excludes`
    adds treatment-name exclusions on top of the shared list, only for terms
    that are wrong at this clinic but fine elsewhere; anything that is never
    an RMT slot belongs in the shared list.
    """
    return JaneAppConfig(
        name=name,
        city=city,
        platform=Platform.JANEAPP,
        subdomain=subdomain,
        location=location,
        services=[
            {
                "type": ServiceType.MASSAGE_THERAPY,
                "durations": DEFAULT_DURATIONS,
                "first_visit_durations": FIRST_VISIT_DURATIONS,
                "first_visit_keywords": FIRST_VISIT_KEYWORDS,
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
    jane_rmt(
        "A Balanced Body", "abalancedbody", location="a-balanced-body-wellness-clinic"
    ),
    jane_rmt("Vitality Treatment Centre", "vitalitytreatment"),
    # Booking page lives under /locations/ rather than on the homepage
    jane_rmt("Tall Tree Health", "talltreehealthjamesbay"),
    jane_rmt("Massage Therapy Group", "massagetherapygroup"),
    # Multi-location Jane accounts: one entry per location (see jane_rmt's location).
    jane_rmt(
        "Equilibrium Massage Therapy (Fisgard)",
        "equilibriummassagetherapy",
        location="equilibrium-therapeutics-fisgard",
    ),
    jane_rmt(
        "Equilibrium Massage Therapy (Tillicum)",
        "equilibriummassagetherapy",
        location="equilibrium-therapeutics-tillicum",
    ),
    jane_rmt(
        "Equilibrium Massage Therapy (Eagle Creek)",
        "equilibriummassagetherapy",
        location="equilibrium-therapeutics-eagle-creek",
    ),
    # Each RMT is a separate Jane "location"; the third is an acupuncturist.
    jane_rmt(
        "Victoria Massage Therapy (Matthew Crotty)",
        "victoriamassagetherapy",
        location="matthew-crotty-rmt-massage-therapy-victoria-rockland",
    ),
    jane_rmt(
        "Victoria Massage Therapy (Noelle Daigle)",
        "victoriamassagetherapy",
        location="noelle-daigle-rmt-massage-therapy-victoria-rockland",
    ),
    # Added 2026-07-09 after web search + location verification
    jane_rmt("Infinity Massage and Acupuncture", "infinitymassage"),
    jane_rmt("Optimal Health Massage Therapy", "optimalhealthmassage"),
    jane_rmt("Glow Integrative Clinic", "glowintegrative"),
    jane_rmt("Heart of the Village Massage Therapy", "heartofthevillagemassagetherapy"),
    # Added 2026-07-23 after web search + location verification
    jane_rmt("Atlas Health Therapy", "atlashealththerapy"),
    jane_rmt("Discovery Health", "discoveryhealth"),
    jane_rmt("Wild Cove Massage Therapy", "wildcovemassagetherapy"),
    jane_rmt("Pearl Healthcare", "pearlhealthcare"),
    # Names its discipline just "Massage" (not "Massage Therapy"), so it
    # needs a per-clinic override.
    jane_rmt(
        "Victoria Centre Acupuncture and Massage",
        "vcaspa",
        discipline_names=["Massage"],
    ),
    # Langford & West Shore — added 2026-10-08 after web search + location
    # verification. Includes Colwood's Wale Rd and Sooke Rd clinics (see
    # docs/plans/multi-city-langford.md).
    jane_rmt("Thetis Massage Therapy", "thetismassage", city="langford"),
    jane_rmt("Westshore Massage Therapy", "westshoremassagetherapy", city="langford"),
    jane_rmt("Aurora Health & Wellness", "aurorahealthclinic", city="langford"),
    jane_rmt("Align Health", "alignhealth", city="langford"),
    jane_rmt("Driftwood Sport & Wellness", "driftwoodhealth", city="langford"),
    jane_rmt("Lucid Integrative Health", "lucidintegrativehealth", city="langford"),
    jane_rmt(
        "Eileen Durant RMT", "eileendurantregisteredmassagetherapy", city="langford"
    ),
    jane_rmt("Story and Depth Massage", "storyanddepthmassage", city="langford"),
    jane_rmt("Sanctum Massage & Wellness", "sanctumwellness", city="langford"),
    jane_rmt("Symmetry Wellness", "symmetryco", city="langford"),
    jane_rmt("Sync Massage Therapy", "synctherapy", city="langford"),
    jane_rmt("Kari Lund RMT", "karilundrmt", city="langford"),
    # Added 2026-10-08 after a second search pass.
    jane_rmt("Riverwood Massage", "riverwoodmassage", city="langford"),
    # First visits are booked as 70-75 min (see FIRST_VISIT_DURATIONS).
    jane_rmt("Christina Baptista RMT", "christinabaptistarmt", city="langford"),
    jane_rmt("Maggie Kay RMT", "maggiekayrmt", city="langford"),
    jane_rmt("Ocean View RMT", "oceanviewrmt", city="langford"),
    # Metchosin counts as West Shore.
    jane_rmt("Metchosin Wellness Collective", "metchosinwellness", city="langford"),
    # Formerly Natural Balance Massage & Health; now one location of a
    # Saanich/Victoria physio account.
    jane_rmt(
        "Natural Balance / Westshore Physio +",
        "saanichphysio",
        city="langford",
        location="westshore",
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
