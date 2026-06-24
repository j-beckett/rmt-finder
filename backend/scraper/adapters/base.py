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
    def discover(self, clinic) -> dict:
        """
        Given a clinic config, discover the platform-specific IDs
        needed to query availability (e.g. discipline_id, treatment_id
        for Jane App).

        Returns a dict of whatever the adapter needs internally.
        Every adapter must implement this method.
        """
        pass