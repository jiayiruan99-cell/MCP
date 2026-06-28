"""Downloads and caches the raw OpenFlights ``.dat`` datasets.

The data layer is the *only* place that touches the network or the filesystem.
Everything above this (domain, MCP tools, assistant) works against parsed,
in-memory objects, which keeps the tool boundary clean and testable.
"""

from __future__ import annotations

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

_BASE = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"

DATA_URLS: dict[str, str] = {
    "airports.dat": f"{_BASE}/airports.dat",
    "airlines.dat": f"{_BASE}/airlines.dat",
    "routes.dat": f"{_BASE}/routes.dat",
}

# Default cache location: <repo>/data
DEFAULT_DATA_DIR = Path(__file__).resolve().parents[3] / "data"


def _env_data_dir() -> Path | None:
    import os

    value = os.environ.get("OPENFLIGHTS_DATA_DIR")
    return Path(value).expanduser() if value else None


def ensure_datasets(data_dir: Path | None = None, *, force: bool = False) -> dict[str, Path]:
    """Ensure all OpenFlights datasets exist locally, downloading if needed.

    Returns a mapping of dataset filename -> local path. The cache directory is
    chosen from (in order): the ``data_dir`` argument, the ``OPENFLIGHTS_DATA_DIR``
    environment variable, then the default ``<repo>/data``.
    """
    target_dir = data_dir or _env_data_dir() or DEFAULT_DATA_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for filename, url in DATA_URLS.items():
        path = target_dir / filename
        if force or not path.exists() or path.stat().st_size == 0:
            logger.info("Downloading %s -> %s", url, path)
            _download(url, path)
        else:
            logger.debug("Using cached dataset %s", path)
        paths[filename] = path
    return paths


def _download(url: str, dest: Path) -> None:
    with httpx.Client(timeout=60.0, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
