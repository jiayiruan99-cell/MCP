"""Typed I/O models for the *airports* capability."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..base import ToolResult


class AirportInfo(BaseModel):
    """A user-facing airport record."""

    iata: str | None = Field(None, description="3-letter IATA code, e.g. 'BER'.")
    icao: str | None = Field(None, description="4-letter ICAO code, e.g. 'EDDB'.")
    name: str
    city: str
    country: str
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None


class FindAirportsResult(ToolResult):
    query: str
    count: int
    airports: list[AirportInfo]
