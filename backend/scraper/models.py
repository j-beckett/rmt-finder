from dataclasses import dataclass
from enum import Enum


class ServiceType(Enum):
    MASSAGE_THERAPY = "massage_therapy"
    ACUPUNCTURE = "acupuncture"
    PHYSIOTHERAPY = "physiotherapy"


@dataclass
class AvailabilityResult:
    clinic_name: str
    city: str
    platform: str
    rmt_name: str
    service_type: ServiceType
    duration_minutes: int
    start_at: str
    booking_url: str