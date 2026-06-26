"""Typed I/O models for the *routes* capability."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ..base import ToolResult


class RouteInfo(BaseModel):  # plain BaseModel; not a standalone tool result
    """A single direct route edge, enriched with airline/airport names."""

    source_iata: str
    source_city: str
    dest_iata: str
    dest_city: str
    airline: str
    airline_iata: str | None = None
    codeshare: bool = False


class FindDirectRoutesResult(ToolResult):
    origin: str
    destination: str
    has_direct_route: bool
    count: int
    routes: list[RouteInfo]
    notes: list[str] = Field(default_factory=list)


class ConnectionInfo(BaseModel):
    """A one-stop itinerary: origin -> hub -> destination."""

    origin_iata: str
    origin_city: str
    hub_iata: str
    hub_city: str
    dest_iata: str
    dest_city: str
    first_leg_airlines: list[str]
    second_leg_airlines: list[str]


class SuggestAlternativesResult(ToolResult):
    origin: str
    destination: str
    direct_available: bool
    count: int
    connections: list[ConnectionInfo]
    notes: list[str] = Field(default_factory=list)
