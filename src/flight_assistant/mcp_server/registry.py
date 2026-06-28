"""Service registry shared by all MCP tool modules.

Loads the OpenFlights repository once and lazily instantiates each domain
service on first use. Tool modules receive the registry and pull whatever
service they need via :meth:`ServiceRegistry.service`, so adding a new
capability never touches the loading or wiring of existing ones.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypeVar

from ..data_access.repository import OpenFlightsRepository

logger = logging.getLogger("flight_mcp")

T = TypeVar("T")


class ServiceRegistry:
    """Lazily provides domain services backed by a shared repository."""

    def __init__(self, *, download: bool = True, data_dir: Path | None = None) -> None:
        self._download = download
        self._data_dir = data_dir
        self._repo: OpenFlightsRepository | None = None
        self._services: dict[type, object] = {}

    @property
    def repo(self) -> OpenFlightsRepository:
        if self._repo is None:
            logger.info("Loading OpenFlights datasets (first call only)...")
            self._repo = OpenFlightsRepository.from_data_dir(
                self._data_dir, download=self._download
            )
            logger.info(
                "Loaded %d airports, %d airlines, %d routes.",
                len(self._repo.airports),
                len(self._repo.airlines),
                len(self._repo.routes),
            )
        return self._repo

    def service(self, service_cls: type[T]) -> T:
        """Return a cached instance of ``service_cls``, creating it if needed.

        Every domain service follows the same constructor contract
        ``service_cls(repo)``, which keeps registration uniform across
        capabilities.
        """
        if service_cls not in self._services:
            self._services[service_cls] = service_cls(self.repo)
        return self._services[service_cls]  # type: ignore[return-value]
