from abc import ABC, abstractmethod
from ..models import AvailabilityResult


class BaseAdapter(ABC):

    @abstractmethod
    def fetch_availability(self, clinic) -> list[AvailabilityResult]:
        """
        Given a clinic config, return a list of available slots
        as AvailabilityResult objects.

        Every adapter must implement this method.
        """
        pass

    @abstractmethod
    def discover(self, clinic, session) -> dict:
        """
        Given a clinic config and an HTTP session, discover the
        platform-specific IDs needed to query availability
        (e.g. discipline_id, treatment_id for Jane App).

        The session is created once per clinic scrape and passed down
        so cookies persist across requests to the same clinic, and so
        adapters stay stateless (safe to share across clinics).

        Returns a dict of whatever the adapter needs internally.
        Every adapter must implement this method.
        """
        pass