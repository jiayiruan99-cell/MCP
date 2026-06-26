"""Typed domain entities parsed from the OpenFlights datasets.

These models describe the *raw* domain objects (airports, airlines, routes).
They are deliberately separate from the per-capability tool I/O models under
``flight_assistant.domain`` so the data layer can evolve independently of the
public tool contract.
"""

from __future__ import annotations

from pydantic import BaseModel


class Airport(BaseModel):
    """A single airport from ``airports.dat``."""

    airport_id: int
    name: str
    city: str
    country: str
    iata: str | None = None  # 3-letter code, e.g. "BER"
    icao: str | None = None  # 4-letter code, e.g. "EDDB"
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None  # Olson tz, e.g. "Europe/Berlin"


class Airline(BaseModel):
    """A single airline from ``airlines.dat``."""

    airline_id: int
    name: str
    iata: str | None = None
    icao: str | None = None
    country: str | None = None
    active: bool = False


class Route(BaseModel):
    """A single historical route edge from ``routes.dat``.

    NOTE: this is *historical* connectivity data, not a live schedule.
    """

    airline_code: str  # IATA/ICAO of the operating airline as written in routes.dat
    airline_id: int | None = None
    source_iata: str
    dest_iata: str
    codeshare: bool = False
    stops: int = 0
    equipment: list[str] = []
