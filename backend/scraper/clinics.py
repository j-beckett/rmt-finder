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
]


def jane_rmt(name: str, subdomain: str, city: str = "victoria") -> JaneAppConfig:
    return JaneAppConfig(
        name=name,
        city=city,
        platform=Platform.JANEAPP,
        subdomain=subdomain,
        services=[
            {
                "type": ServiceType.MASSAGE_THERAPY,
                "durations": DEFAULT_DURATIONS,
                "discipline_names": DEFAULT_DISCIPLINE_NAMES,
                "exclude_treatment_keywords": EXCLUDED_TREATMENT_KEYWORDS,
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
    # Needs investigation
    # jane_rmt("Tall Tree Health", "talltreehealthjamesbay"), needs better location filter
    # jane_rmt("Massotherapy Group", "massotherapygroup"),
    # jane_rmt("Solace Massage", "solacemassagevictoria"), dupes
    # New ones to test
]
