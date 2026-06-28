"""Route-discovery domain service.

Turns fuzzy user inputs (city, IATA code, country) into deterministic,
structured route answers using the repository. Pure Python — no MCP/LLM — so it
is fully unit-testable in isolation.
"""

from __future__ import annotations

from collections import defaultdict

from ...data_access.repository import OpenFlightsRepository
from .models import (
    ConnectionInfo,
    FindDirectRoutesResult,
    RouteInfo,
    SuggestAlternativesResult,
)


class RouteDiscoveryService:
    """Direct-route and one-stop-alternative operations."""

    def __init__(self, repo: OpenFlightsRepository) -> None:
        self.repo = repo

    # ------------------------------------------------------------- helpers
    def _resolve_airports(self, location: str):
        """Resolve a free-text location to candidate airports with IATA codes.

        Accepts an IATA code, a city name, or an airport name. Only airports
        that actually have an IATA code (and thus can appear in routes) are
        returned.
        """
        matches = self.repo.search_airports(location, limit=25)
        return [ap for ap in matches if ap.iata]

    # ------------------------------------------------------------- direct
    def find_direct_routes(self, origin: str, destination: str) -> FindDirectRoutesResult:
        origins = self._resolve_airports(origin)
        dests = self._resolve_airports(destination)
        notes: list[str] = []

        if not origins:
            notes.append(f"Could not resolve origin '{origin}' to any airport with an IATA code.")
        if not dests:
            notes.append(f"Could not resolve destination '{destination}' to any airport with an IATA code.")

        routes: list[RouteInfo] = []
        dest_iatas = {ap.iata.upper(): ap for ap in dests if ap.iata}
        for o in origins:
            # _resolve_airports() guarantees every origin has an IATA code.
            # Iterate departing routes once and filter by the destination set.
            for r in self.repo.routes_from.get(o.iata.upper(), []):
                if r.stops != 0:
                    continue
                d_ap = dest_iatas.get(r.dest_iata.upper())
                if not d_ap:
                    continue
                airline = self.repo.airline_name(r)
                airline_iata = None
                if r.airline_id and r.airline_id in self.repo.airline_by_id:
                    airline_iata = self.repo.airline_by_id[r.airline_id].iata
                routes.append(
                    RouteInfo(
                        source_iata=o.iata.upper(),
                        source_city=o.city,
                        dest_iata=r.dest_iata.upper(),
                        dest_city=d_ap.city,
                        airline=airline,
                        airline_iata=airline_iata,
                        codeshare=r.codeshare,
                    )
                )

        # De-duplicate identical (src, dst, airline) tuples.
        routes = _dedupe_routes(routes)

        if origins and dests and not routes:
            notes.append("No direct route found in the historical data. Try suggest_alternative_routes for one-stop options.")

        return FindDirectRoutesResult(
            origin=origin,
            destination=destination,
            has_direct_route=bool(routes),
            count=len(routes),
            routes=routes,
            notes=notes,
        )

    # ------------------------------------------------------------- alternatives
    def suggest_alternative_routes(
        self, origin: str, destination: str, limit: int = 5
    ) -> SuggestAlternativesResult:
        origins = self._resolve_airports(origin)
        dests = self._resolve_airports(destination)
        notes: list[str] = []

        if not origins or not dests:
            if not origins:
                notes.append(f"Could not resolve origin '{origin}'.")
            if not dests:
                notes.append(f"Could not resolve destination '{destination}'.")
            return SuggestAlternativesResult(
                origin=origin,
                destination=destination,
                direct_available=False,
                count=0,
                connections=[],
                notes=notes,
            )

        # Is a direct route available? (informational)
        direct = self.find_direct_routes(origin, destination)

        origin_iatas = {ap.iata.upper(): ap for ap in origins if ap.iata}
        dest_iatas = {ap.iata.upper(): ap for ap in dests if ap.iata}

        # Destinations reachable in one hop from any origin -> potential hubs.
        first_leg: dict[str, set[str]] = defaultdict(set)
        first_leg_origin: dict[str, str] = {}  # hub -> origin iata used
        for o_iata, o_ap in origin_iatas.items():
            for r in self.repo.routes_from.get(o_iata, []):
                if r.stops != 0:
                    continue
                hub = r.dest_iata.upper()
                if hub in dest_iatas or hub in origin_iatas:
                    continue
                first_leg[hub].add(self.repo.airline_name(r))
                first_leg_origin.setdefault(hub, o_iata)

        connections: list[ConnectionInfo] = []
        for hub, first_airlines in first_leg.items():
            # Second leg: hub -> any destination.
            second_airlines_by_dest: dict[str, set[str]] = defaultdict(set)
            for r in self.repo.routes_from.get(hub, []):
                if r.stops != 0:
                    continue
                if r.dest_iata.upper() in dest_iatas:
                    second_airlines_by_dest[r.dest_iata.upper()].add(self.repo.airline_name(r))

            for d_iata, second_airlines in second_airlines_by_dest.items():
                hub_ap = self.repo.airport_by_iata.get(hub)
                o_ap = origin_iatas[first_leg_origin[hub]]
                d_ap = dest_iatas[d_iata]
                connections.append(
                    ConnectionInfo(
                        origin_iata=o_ap.iata.upper(),
                        origin_city=o_ap.city,
                        hub_iata=hub,
                        hub_city=hub_ap.city if hub_ap else hub,
                        dest_iata=d_iata,
                        dest_city=d_ap.city,
                        first_leg_airlines=sorted(first_airlines),
                        second_leg_airlines=sorted(second_airlines),
                    )
                )

        # Prefer hubs served by more airlines (rough proxy for "good" hubs).
        connections.sort(
            key=lambda c: len(c.first_leg_airlines) + len(c.second_leg_airlines),
            reverse=True,
        )
        connections = connections[:limit]

        if direct.has_direct_route:
            notes.append("A direct route also exists; these one-stop options are provided as alternatives.")
        if not connections:
            notes.append("No one-stop connection found in the historical data.")

        return SuggestAlternativesResult(
            origin=origin,
            destination=destination,
            direct_available=direct.has_direct_route,
            count=len(connections),
            connections=connections,
            notes=notes,
        )


def _dedupe_routes(routes: list[RouteInfo]) -> list[RouteInfo]:
    seen: set[tuple[str, str, str]] = set()
    out: list[RouteInfo] = []
    for r in routes:
        key = (r.source_iata, r.dest_iata, r.airline)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out
