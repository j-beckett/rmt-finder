from dataclasses import dataclass, field
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


CLINICS = [
    JaneAppConfig(
        name="Geometry",
        city="victoria",
        platform=Platform.JANEAPP,
        subdomain="geometry",
        services=[
            {"type": ServiceType.MASSAGE_THERAPY, "durations": [60]}
        ]
    ),
]