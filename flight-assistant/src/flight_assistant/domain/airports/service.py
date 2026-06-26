"""Airport-search domain service.

Pure logic over the OpenFlights repository: resolve a free-text query (city,
country, IATA code, or airport name) to structured airport records. No MCP or
LLM involvement, so it is fully unit-testable in isolation.
"""

from __future__ import annotations

from ...data_access.models import Airport
from ...data_access.repository import OpenFlightsRepository
from .models import AirportInfo, FindAirportsResult


def to_airport_info(ap: Airport) -> AirportInfo:
    """Convert a raw data-layer Airport into the public AirportInfo model."""
    return AirportInfo(
        iata=ap.iata,
        icao=ap.icao,
        name=ap.name,
        city=ap.city,
        country=ap.country,
        latitude=ap.latitude,
        longitude=ap.longitude,
        timezone=ap.timezone,
    )


class AirportService:
    """Airport lookup operations."""

    def __init__(self, repo: OpenFlightsRepository) -> None:
        self.repo = repo

    def find_airports(self, query: str, limit: int = 10) -> FindAirportsResult:
        airports = self.repo.search_airports(query, limit=limit)
        return FindAirportsResult(
            query=query,
            count=len(airports),
            airports=[to_airport_info(ap) for ap in airports],
        )
