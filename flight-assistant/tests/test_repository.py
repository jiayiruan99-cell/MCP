"""Tests for the parsing and indexing in OpenFlightsRepository."""

from __future__ import annotations

from flight_assistant.data_access.repository import OpenFlightsRepository


def test_airports_parsed_and_indexed(repo: OpenFlightsRepository) -> None:
    assert len(repo.airports) == 5
    assert "BER" in repo.airport_by_iata
    assert repo.airport_by_iata["BER"].city == "Berlin"
    assert repo.airport_by_iata["LIS"].country == "Portugal"


def test_search_by_iata(repo: OpenFlightsRepository) -> None:
    results = repo.search_airports("LIS")
    assert results and results[0].iata == "LIS"


def test_search_by_city(repo: OpenFlightsRepository) -> None:
    results = repo.search_airports("Berlin")
    assert any(ap.iata == "BER" for ap in results)


def test_search_by_country(repo: OpenFlightsRepository) -> None:
    results = repo.search_airports("Portugal")
    iatas = {ap.iata for ap in results}
    assert {"LIS", "OPO"}.issubset(iatas)


def test_search_by_name_substring(repo: OpenFlightsRepository) -> None:
    results = repo.search_airports("Kennedy")
    assert any(ap.iata == "JFK" for ap in results)


def test_direct_routes_index(repo: OpenFlightsRepository) -> None:
    routes = repo.direct_routes("BER", "LIS")
    assert len(routes) == 1
    assert routes[0].source_iata == "BER"
    assert routes[0].dest_iata == "LIS"


def test_destinations_from(repo: OpenFlightsRepository) -> None:
    dests = repo.destinations_from("FRA")
    assert {"LIS", "JFK"}.issubset(dests)


def test_airline_name_resolution(repo: OpenFlightsRepository) -> None:
    route = repo.direct_routes("BER", "LIS")[0]
    assert repo.airline_name(route) == "Lufthansa"
