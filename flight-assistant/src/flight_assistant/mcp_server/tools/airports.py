"""MCP tool module for the *airports* capability."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ...domain.airports.models import FindAirportsResult
from ...domain.airports.service import AirportService
from ..registry import ServiceRegistry


def register(mcp: FastMCP, registry: ServiceRegistry) -> None:
    """Register airport tools on the given MCP server."""

    @mcp.tool()
    def find_airports(query: str, limit: int = 10) -> FindAirportsResult:
        """Find airports by city, country, IATA code, or airport name.

        Args:
            query: A city ("Berlin"), country ("Portugal"), IATA code ("BER"),
                or part of an airport name ("Tegel").
            limit: Maximum number of airports to return (default 10).
        """
        return registry.service(AirportService).find_airports(query=query, limit=limit)
