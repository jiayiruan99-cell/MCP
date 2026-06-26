"""MCP server exposing route-discovery capabilities as typed tools.

This is the *integration boundary*. The assistant never imports the domain
services or the data layer directly — it only sees the tools registered here
over the Model Context Protocol (stdio transport by default).

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

# Each entry exposes ``register(mcp, registry)``.
CAPABILITY_MODULES = (airports, routes)

mcp = FastMCP("flight-route-discovery")
_registry = ServiceRegistry()

for _module in CAPABILITY_MODULES:
    _module.register(mcp, _registry)


def main() -> None:
    """Run the MCP server over stdio (default transport)."""
    mcp.run()


if __name__ == "__main__":
    main()

