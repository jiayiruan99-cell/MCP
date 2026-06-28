"""MCP server exposing route-discovery capabilities as typed tools.

This is the *integration boundary*. The assistant never imports the domain
services or the data layer directly — it only sees the tools registered here
over the Model Context Protocol.

The transport is configurable (``MCP_TRANSPORT``):

  * ``stdio`` (default) — local subprocess transport used by local MCP hosts
    (Claude Desktop / VS Code).
  * ``streamable-http`` / ``sse`` — networked transports for hosting the server
    as a remote connector (e.g. behind TLS + auth for ChatGPT / Claude Team).
    The in-repo agent auto-starts the server over ``streamable-http``.

Capabilities are registered from per-capability modules in ``tools/``. Adding a
new capability is a two-line change: import its module and add it to
``CAPABILITY_MODULES`` — no existing tool is touched.
"""

from __future__ import annotations

import logging
import os

from mcp.server.fastmcp import FastMCP

from ..config import load_config
from .registry import ServiceRegistry
from .tools import airports, routes

load_config()
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))

logger = logging.getLogger("flight_mcp")

# Each entry exposes ``register(mcp, registry)``.
CAPABILITY_MODULES = (airports, routes)

# Host/port only matter for the networked (HTTP/SSE) transports; they are
# harmless for stdio. They are read here so a single FastMCP instance serves
# every transport.
_HOST = os.environ.get("MCP_HOST", "127.0.0.1")
_PORT = int(os.environ.get("MCP_PORT", "8000"))

mcp = FastMCP("flight-route-discovery", host=_HOST, port=_PORT)
_registry = ServiceRegistry()

for _module in CAPABILITY_MODULES:
    _module.register(mcp, _registry)

# Accepted transports, with a friendly alias for "http".
_TRANSPORTS = {
    "stdio": "stdio",
    "sse": "sse",
    "streamable-http": "streamable-http",
    "http": "streamable-http",
}


def _resolve_transport() -> str:
    """Pick the transport from ``MCP_TRANSPORT`` (default ``stdio``)."""
    requested = os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()
    transport = _TRANSPORTS.get(requested)
    if transport is None:
        valid = ", ".join(sorted(_TRANSPORTS))
        raise SystemExit(
            f"Unknown MCP_TRANSPORT {requested!r}. Valid values: {valid}."
        )
    return transport


def main() -> None:
    """Run the MCP server over the configured transport (default: stdio)."""
    transport = _resolve_transport()
    if transport == "stdio":
        logger.info("Starting MCP server over stdio.")
    else:
        logger.info(
            "Starting MCP server over %s on %s:%s", transport, _HOST, _PORT
        )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()

