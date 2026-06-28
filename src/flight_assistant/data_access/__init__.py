"""Data access layer: the only place that touches files/network."""

from .loader import ensure_datasets
from .models import Airline, Airport, Route
from .repository import OpenFlightsRepository

__all__ = ["ensure_datasets", "Airline", "Airport", "Route", "OpenFlightsRepository"]
