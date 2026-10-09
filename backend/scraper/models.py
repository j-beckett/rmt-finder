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
    treatment_name: str
    duration_minutes: int
    start_at: str
    booking_url: str


@dataclass
class RunResult:
    """Outcome of one scrape run: per-clinic results plus the slots found."""

    slots: list[AvailabilityResult]
    attempted: list[str]
    succeeded: list[str]
    failed: list[str]