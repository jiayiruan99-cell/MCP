"""MCP tool module for the *routes* capability."""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from ...domain.routes.models import FindDirectRoutesResult, SuggestAlternativesResult
from ...domain.routes.service import RouteDiscoveryService
from ..registry import ServiceRegistry


def register(mcp: FastMCP, registry: ServiceRegistry) -> None:
    """Register route-discovery tools on the given MCP server."""

    @mcp.tool()
    def find_direct_routes(origin: str, destination: str) -> FindDirectRoutesResult:
        """Find direct (non-stop) routes between two places, per historical data.

        Origin/destination may each be an IATA code, a city, or an airport name.
        Returns every historical non-stop route plus the operating airline(s).

        NOTE: results come from historical OpenFlights data and are NOT a live
        schedule. The response includes a disclaimer field reflecting this.
        """
        return registry.service(RouteDiscoveryService).find_direct_routes(
            origin=origin, destination=destination
        )

    @mcp.tool()
    def suggest_alternative_routes(
        origin: str, destination: str, limit: int = 5
    ) -> SuggestAlternativesResult:
        """Suggest simple one-stop connections when a direct route is unhelpful.

        Returns up to ``limit`` itineraries of the form origin -> hub ->
        destination, ranked by how many airlines serve each leg. Also reports
        whether a direct route exists.
        """
        return registry.service(RouteDiscoveryService).suggest_alternative_routes(
            origin=origin, destination=destination, limit=limit
        )
