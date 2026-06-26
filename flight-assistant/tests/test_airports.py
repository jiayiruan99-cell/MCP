"""Tests for the airports capability (AirportService)."""

from __future__ import annotations

from flight_assistant.domain.base import OPENFLIGHTS_DISCLAIMER
from flight_assistant.domain.airports.service import AirportService


def test_find_airports_returns_disclaimer(airport_service: AirportService) -> None:
    res = airport_service.find_airports("Berlin")
    assert res.count >= 1
    assert res.disclaimer == OPENFLIGHTS_DISCLAIMER
    assert res.airports[0].city == "Berlin"


def test_find_airports_by_iata(airport_service: AirportService) -> None:
    res = airport_service.find_airports("LIS")
    assert any(ap.iata == "LIS" for ap in res.airports)


def test_find_airports_by_country(airport_service: AirportService) -> None:
    res = airport_service.find_airports("Portugal")
    iatas = {ap.iata for ap in res.airports}
    assert {"LIS", "OPO"}.issubset(iatas)
