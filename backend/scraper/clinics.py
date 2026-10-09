from dataclasses import dataclass
from enum import Enum
from .models import ServiceType


class Platform(Enum):
    JANEAPP = "janeapp"
    MINDBODY = "mindbody"


@dataclass
class ClinicConfig:
    name: str
    # Stable analytics key; never derive it from name, which can be edited.
    slug: str
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
    *,
    slug: str,
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
        slug=slug,
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
    jane_rmt("Geometry", "geometry", slug="geometry"),
    jane_rmt("ViVi Therapy", "vivitherapy", slug="vivi-therapy"),
    jane_rmt("Remedy Wellness Centre", "remedywellnesscentre", slug="remedy-wellness"),
    jane_rmt("Saanich Massage", "saanichmassage", slug="saanich-massage"),
    jane_rmt("Joseph Fisher RMT", "jfrmt", slug="joseph-fisher-rmt"),
    jane_rmt(
        "Massage Therapy Clinic",
        "massagetherapyclinic",
        slug="massage-therapy-clinic",
    ),
    jane_rmt(
        "Downtown Victoria Massage",
        "downtownvictoriamassagetherapy",
        slug="downtown-victoria-massage",
    ),
    jane_rmt("Victoria Clayton RMT", "victoriaclaytonrmt", slug="victoria-clayton-rmt"),
    # New to test
    jane_rmt("Synergy Massage", "synergymassage", slug="synergy-massage"),
    jane_rmt("The Lab Victoria", "labvictoria", slug="lab-victoria"),
    jane_rmt("Active Health Clinic", "activehealthclinic", slug="active-health"),
    jane_rmt("Reach Health", "reachhealth", slug="reach-health"),
    jane_rmt("Renew Health", "renew", slug="renew-health"),
    jane_rmt(
        "A Balanced Body",
        "abalancedbody",
        slug="a-balanced-body",
        location="a-balanced-body-wellness-clinic",
    ),
    jane_rmt(
        "Vitality Treatment Centre",
        "vitalitytreatment",
        slug="vitality-treatment",
    ),
    # Booking page lives under /locations/ rather than on the homepage
    jane_rmt("Tall Tree Health", "talltreehealthjamesbay", slug="tall-tree-james-bay"),
    jane_rmt(
        "Massage Therapy Group",
        "massagetherapygroup",
        slug="massage-therapy-group",
    ),
    # Multi-location Jane accounts: one entry per location (see jane_rmt's location).
    jane_rmt(
        "Equilibrium Massage Therapy (Fisgard)",
        "equilibriummassagetherapy",
        slug="equilibrium-fisgard",
        location="equilibrium-therapeutics-fisgard",
    ),
    jane_rmt(
        "Equilibrium Massage Therapy (Tillicum)",
        "equilibriummassagetherapy",
        slug="equilibrium-tillicum",
        location="equilibrium-therapeutics-tillicum",
    ),
    jane_rmt(
        "Equilibrium Massage Therapy (Eagle Creek)",
        "equilibriummassagetherapy",
        slug="equilibrium-eagle-creek",
        location="equilibrium-therapeutics-eagle-creek",
    ),
    # Each RMT is a separate Jane "location"; the third is an acupuncturist.
    jane_rmt(
        "Victoria Massage Therapy (Matthew Crotty)",
        "victoriamassagetherapy",
        slug="victoria-massage-crotty",
        location="matthew-crotty-rmt-massage-therapy-victoria-rockland",
    ),
    jane_rmt(
        "Victoria Massage Therapy (Noelle Daigle)",
        "victoriamassagetherapy",
        slug="victoria-massage-daigle",
        location="noelle-daigle-rmt-massage-therapy-victoria-rockland",
    ),
    # Added 2026-07-09 after web search + location verification
    jane_rmt(
        "Infinity Massage and Acupuncture",
        "infinitymassage",
        slug="infinity-massage",
    ),
    jane_rmt(
        "Optimal Health Massage Therapy",
        "optimalhealthmassage",
        slug="optimal-health-massage",
    ),
    jane_rmt("Glow Integrative Clinic", "glowintegrative", slug="glow-integrative"),
    jane_rmt(
        "Heart of the Village Massage Therapy",
        "heartofthevillagemassagetherapy",
        slug="heart-of-the-village",
    ),
    # Added 2026-07-23 after web search + location verification
    jane_rmt("Atlas Health Therapy", "atlashealththerapy", slug="atlas-health"),
    jane_rmt("Discovery Health", "discoveryhealth", slug="discovery-health"),
    jane_rmt(
        "Wild Cove Massage Therapy",
        "wildcovemassagetherapy",
        slug="wild-cove-massage",
    ),
    jane_rmt("Pearl Healthcare", "pearlhealthcare", slug="pearl-healthcare"),
    # Names its discipline just "Massage" (not "Massage Therapy"), so it
    # needs a per-clinic override.
    jane_rmt(
        "Victoria Centre Acupuncture and Massage",
        "vcaspa",
        slug="victoria-centre-acupuncture",
        discipline_names=["Massage"],
    ),
    # Langford & West Shore — added 2026-10-08 after web search + location
    # verification. Includes Colwood's Wale Rd and Sooke Rd clinics (see
    # docs/plans/multi-city-langford.md).
    jane_rmt(
        "Thetis Massage Therapy",
        "thetismassage",
        slug="thetis-massage",
        city="langford",
    ),
    jane_rmt(
        "Westshore Massage Therapy",
        "westshoremassagetherapy",
        slug="westshore-massage",
        city="langford",
    ),
    jane_rmt(
        "Aurora Health & Wellness",
        "aurorahealthclinic",
        slug="aurora-health",
        city="langford",
    ),
    jane_rmt("Align Health", "alignhealth", slug="align-health", city="langford"),
    jane_rmt(
        "Driftwood Sport & Wellness",
        "driftwoodhealth",
        slug="driftwood-sport-wellness",
        city="langford",
    ),
    jane_rmt(
        "Lucid Integrative Health",
        "lucidintegrativehealth",
        slug="lucid-integrative",
        city="langford",
    ),
    jane_rmt(
        "Eileen Durant RMT",
        "eileendurantregisteredmassagetherapy",
        slug="eileen-durant-rmt",
        city="langford",
    ),
    jane_rmt(
        "Story and Depth Massage",
        "storyanddepthmassage",
        slug="story-and-depth",
        city="langford",
    ),
    jane_rmt(
        "Sanctum Massage & Wellness",
        "sanctumwellness",
        slug="sanctum-wellness",
        city="langford",
    ),
    jane_rmt(
        "Symmetry Wellness",
        "symmetryco",
        slug="symmetry-wellness",
        city="langford",
    ),
    jane_rmt(
        "Sync Massage Therapy",
        "synctherapy",
        slug="sync-massage",
        city="langford",
    ),
    jane_rmt("Kari Lund RMT", "karilundrmt", slug="kari-lund-rmt", city="langford"),
    # Added 2026-10-08 after a second search pass.
    jane_rmt(
        "Riverwood Massage",
        "riverwoodmassage",
        slug="riverwood-massage",
        city="langford",
    ),
    # First visits are booked as 70-75 min (see FIRST_VISIT_DURATIONS).
    jane_rmt(
        "Christina Baptista RMT",
        "christinabaptistarmt",
        slug="christina-baptista-rmt",
        city="langford",
    ),
    jane_rmt("Maggie Kay RMT", "maggiekayrmt", slug="maggie-kay-rmt", city="langford"),
    jane_rmt("Ocean View RMT", "oceanviewrmt", slug="ocean-view-rmt", city="langford"),
    # Metchosin counts as West Shore.
    jane_rmt(
        "Metchosin Wellness Collective",
        "metchosinwellness",
        slug="metchosin-wellness",
        city="langford",
    ),
    # Formerly Natural Balance Massage & Health; now one location of a
    # Saanich/Victoria physio account.
    jane_rmt(
        "Natural Balance / Westshore Physio +",
        "saanichphysio",
        slug="natural-balance",
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
