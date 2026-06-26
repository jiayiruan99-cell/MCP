"""Shared test fixtures: a tiny, hand-built OpenFlights dataset.

Using small inline data keeps the domain/repository tests fast, deterministic,
and free of any network dependency.
"""

from __future__ import annotations

import pytest

from flight_assistant.data_access.repository import OpenFlightsRepository
from flight_assistant.domain.airports.service import AirportService
from flight_assistant.domain.routes.service import RouteDiscoveryService

# Minimal airports.dat-style rows (id, name, city, country, iata, icao, lat, lon, ...).
AIRPORTS = """\
1,"Berlin Brandenburg Airport","Berlin","Germany","BER","EDDB",52.35,13.49,157,1,"E","Europe/Berlin","airport","OurAirports"
2,"Humberto Delgado Airport","Lisbon","Portugal","LIS","LPPT",38.78,-9.13,374,0,"E","Europe/Lisbon","airport","OurAirports"
3,"Frankfurt am Main Airport","Frankfurt","Germany","FRA","EDDF",50.03,8.57,364,1,"E","Europe/Berlin","airport","OurAirports"
4,"Francisco Sa Carneiro Airport","Porto","Portugal","OPO","LPPR",41.24,-8.68,228,0,"E","Europe/Lisbon","airport","OurAirports"
5,"John F Kennedy International Airport","New York","United States","JFK","KJFK",40.64,-73.78,13,-5,"A","America/New_York","airport","OurAirports"
"""

AIRLINES = """\
10,"Lufthansa","","LH","DLH","LUFTHANSA","Germany","Y"
20,"TAP Air Portugal","","TP","TAP","AIR PORTUGAL","Portugal","Y"
"""

# routes.dat: airline, airline_id, src, src_id, dst, dst_id, codeshare, stops, equip
ROUTES = """\
LH,10,BER,1,FRA,3,,0,32A
LH,10,FRA,3,LIS,2,,0,32A
TP,20,LIS,2,OPO,4,,0,32A
LH,10,FRA,3,JFK,5,,0,74H
LH,10,BER,1,LIS,2,,0,32A
"""


@pytest.fixture()
def repo() -> OpenFlightsRepository:
    from flight_assistant.data_access.repository import (
        parse_airlines,
        parse_airports,
        parse_routes,
    )

    return OpenFlightsRepository(
        airports=parse_airports(AIRPORTS),
        airlines=parse_airlines(AIRLINES),
        routes=parse_routes(ROUTES),
    )


@pytest.fixture()
def airport_service(repo: OpenFlightsRepository) -> AirportService:
    return AirportService(repo)


@pytest.fixture()
def route_service(repo: OpenFlightsRepository) -> RouteDiscoveryService:
    return RouteDiscoveryService(repo)
