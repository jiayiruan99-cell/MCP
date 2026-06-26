"""Parses OpenFlights ``.dat`` files and builds in-memory query indexes.

The repository is a thin, dependency-free data layer:
  * parse the CSV-ish ``.dat`` files into typed models
  * build lookup indexes (by IATA, by city, by country, route adjacency)
  * expose simple, deterministic query primitives

It contains **no LLM and no presentation logic** — that lives in the domain
service and the assistant. This makes it independently unit-testable.
"""

from __future__ import annotations

import csv
import io
from collections import defaultdict
from pathlib import Path

from .loader import ensure_datasets
from .models import Airline, Airport, Route

_NULL = "\\N"


def _clean(value: str) -> str | None:
    value = value.strip()
    if value == "" or value == _NULL:
        return None
    return value


class OpenFlightsRepository:
    """In-memory repository over the OpenFlights datasets."""

    def __init__(
        self,
        airports: list[Airport],
        airlines: list[Airline],
        routes: list[Route],
    ) -> None:
        self.airports = airports
        self.airlines = airlines
        self.routes = routes

        # --- indexes -------------------------------------------------------
        self.airport_by_iata: dict[str, Airport] = {}
        self.airport_by_id: dict[int, Airport] = {}
        self.airports_by_city: dict[str, list[Airport]] = defaultdict(list)
        self.airports_by_country: dict[str, list[Airport]] = defaultdict(list)
        for ap in airports:
            self.airport_by_id[ap.airport_id] = ap
            if ap.iata:
                self.airport_by_iata[ap.iata.upper()] = ap
            if ap.city:
                self.airports_by_city[ap.city.lower()].append(ap)
            if ap.country:
                self.airports_by_country[ap.country.lower()].append(ap)

        self.airline_by_id: dict[int, Airline] = {a.airline_id: a for a in airlines}

        # Adjacency: source IATA -> list of routes departing from it.
        self.routes_from: dict[str, list[Route]] = defaultdict(list)
        for r in routes:
            self.routes_from[r.source_iata.upper()].append(r)

    # ------------------------------------------------------------------ build
    @classmethod
    def from_data_dir(cls, data_dir: Path | None = None, *, download: bool = True) -> "OpenFlightsRepository":
        """Load a repository from a data directory, downloading if needed."""
        if download:
            paths = ensure_datasets(data_dir)
        else:
            from .loader import DEFAULT_DATA_DIR

            base = data_dir or DEFAULT_DATA_DIR
            paths = {name: base / name for name in ("airports.dat", "airlines.dat", "routes.dat")}

        return cls(
            airports=parse_airports(paths["airports.dat"].read_text(encoding="utf-8")),
            airlines=parse_airlines(paths["airlines.dat"].read_text(encoding="utf-8")),
            routes=parse_routes(paths["routes.dat"].read_text(encoding="utf-8")),
        )

    # ----------------------------------------------------------------- queries
    def airline_name(self, route: Route) -> str:
        if route.airline_id and route.airline_id in self.airline_by_id:
            return self.airline_by_id[route.airline_id].name
        return route.airline_code

    def search_airports(self, query: str, limit: int = 10) -> list[Airport]:
        """Find airports by IATA code, city, country, or (substring) name."""
        q = query.strip()
        if not q:
            return []
        ql = q.lower()
        results: list[Airport] = []
        seen: set[int] = set()

        def add(ap: Airport) -> None:
            if ap.airport_id not in seen:
                seen.add(ap.airport_id)
                results.append(ap)

        # 1. Exact IATA match (highest precision).
        if len(q) == 3 and q.upper() in self.airport_by_iata:
            add(self.airport_by_iata[q.upper()])

        # 2. Exact city match.
        for ap in self.airports_by_city.get(ql, []):
            add(ap)

        # 3. Exact country match.
        for ap in self.airports_by_country.get(ql, []):
            add(ap)

        # 4. Substring match on name / city.
        if len(results) < limit:
            for ap in self.airports:
                if ql in ap.name.lower() or ql in ap.city.lower():
                    add(ap)
                if len(results) >= limit:
                    break

        return results[:limit]

    def direct_routes(self, source_iata: str, dest_iata: str) -> list[Route]:
        """All historical direct (0-stop) routes from source to destination."""
        src = source_iata.upper()
        dst = dest_iata.upper()
        return [r for r in self.routes_from.get(src, []) if r.dest_iata.upper() == dst and r.stops == 0]

    def destinations_from(self, source_iata: str) -> set[str]:
        """Set of destination IATA codes reachable directly from a source."""
        return {r.dest_iata.upper() for r in self.routes_from.get(source_iata.upper(), [])}


# ---------------------------------------------------------------------- parsers
def parse_airports(text: str) -> list[Airport]:
    airports: list[Airport] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 8:
            continue
        try:
            airports.append(
                Airport(
                    airport_id=int(row[0]),
                    name=row[1].strip(),
                    city=row[2].strip(),
                    country=row[3].strip(),
                    iata=_clean(row[4]),
                    icao=_clean(row[5]),
                    latitude=_to_float(row[6]),
                    longitude=_to_float(row[7]),
                    timezone=_clean(row[11]) if len(row) > 11 else None,
                )
            )
        except (ValueError, IndexError):
            continue
    return airports


def parse_airlines(text: str) -> list[Airline]:
    airlines: list[Airline] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 8:
            continue
        try:
            airlines.append(
                Airline(
                    airline_id=int(row[0]),
                    name=row[1].strip(),
                    iata=_clean(row[3]),
                    icao=_clean(row[4]),
                    country=_clean(row[6]),
                    active=row[7].strip().upper() == "Y",
                )
            )
        except (ValueError, IndexError):
            continue
    return airlines


def parse_routes(text: str) -> list[Route]:
    routes: list[Route] = []
    for row in csv.reader(io.StringIO(text)):
        if len(row) < 9:
            continue
        src = _clean(row[2])
        dst = _clean(row[4])
        if not src or not dst:
            continue
        try:
            stops = int(row[7]) if row[7].strip().isdigit() else 0
            airline_id = int(row[1]) if row[1].strip().isdigit() else None
            equipment = [e for e in row[8].strip().split(" ") if e]
            routes.append(
                Route(
                    airline_code=row[0].strip(),
                    airline_id=airline_id,
                    source_iata=src,
                    dest_iata=dst,
                    codeshare=row[6].strip().upper() == "Y",
                    stops=stops,
                    equipment=equipment,
                )
            )
        except (ValueError, IndexError):
            continue
    return routes


def _to_float(value: str) -> float | None:
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
