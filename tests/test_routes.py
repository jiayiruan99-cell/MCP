"""Tests for the routes capability (RouteDiscoveryService)."""

from __future__ import annotations

from flight_assistant.domain.routes.service import RouteDiscoveryService


def test_direct_route_by_city(route_service: RouteDiscoveryService) -> None:
    res = route_service.find_direct_routes("Berlin", "Lisbon")
    assert res.has_direct_route is True
    assert res.count == 1
    assert res.routes[0].source_iata == "BER"
    assert res.routes[0].dest_iata == "LIS"
    assert res.routes[0].airline == "Lufthansa"


def test_direct_route_by_iata(route_service: RouteDiscoveryService) -> None:
    res = route_service.find_direct_routes("BER", "FRA")
    assert res.has_direct_route is True


def test_no_direct_route_gives_note(route_service: RouteDiscoveryService) -> None:
    # No direct BER -> JFK in the fixture (only via FRA).
    res = route_service.find_direct_routes("Berlin", "New York")
    assert res.has_direct_route is False
    assert res.count == 0
    assert any("No direct route" in n for n in res.notes)


def test_suggest_alternative_one_stop(route_service: RouteDiscoveryService) -> None:
    # BER -> FRA -> JFK should be discovered.
    res = route_service.suggest_alternative_routes("Berlin", "New York")
    assert res.count >= 1
    hubs = {c.hub_iata for c in res.connections}
    assert "FRA" in hubs
    conn = next(c for c in res.connections if c.hub_iata == "FRA")
    assert conn.origin_iata == "BER"
    assert conn.dest_iata == "JFK"


def test_unresolved_origin_is_reported(route_service: RouteDiscoveryService) -> None:
    res = route_service.find_direct_routes("Nowhereville", "Lisbon")
    assert res.has_direct_route is False
    assert any("Could not resolve origin" in n for n in res.notes)
