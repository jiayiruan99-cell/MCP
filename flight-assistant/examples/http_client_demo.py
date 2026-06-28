"""Connect to the MCP server over the streamable-HTTP transport.

This mirrors how a *remote* MCP host (e.g. a ChatGPT / Claude Team connector)
talks to the server: by connecting to an already-running server over HTTP. The
in-repo agent uses the same HTTP transport but auto-starts its own server
subprocess; here you start the server yourself in a separate terminal. It
initializes a session, lists the advertised tools, and calls one — exercising
the full networked tool boundary end-to-end.

Usage
-----
1. Start the server over HTTP in one terminal::

       MCP_TRANSPORT=http MCP_PORT=8765 flight-mcp-server

2. Run this demo in another::

       python examples/http_client_demo.py
       # or point it elsewhere:
       python examples/http_client_demo.py http://127.0.0.1:8765/mcp

The server itself does not authenticate callers; in a real deployment it must
sit behind TLS + auth (API gateway / reverse proxy / org SSO).
"""

from __future__ import annotations

import sys

import anyio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

DEFAULT_URL = "http://127.0.0.1:8765/mcp"


async def run(url: str) -> None:
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("Tools advertised over HTTP:", [t.name for t in tools.tools])

            result = await session.call_tool(
                "find_direct_routes",
                {"origin": "Berlin", "destination": "Lisbon"},
            )
            data = result.structuredContent or {}
            print("\nfind_direct_routes(Berlin -> Lisbon):")
            print("  has_direct_route:", data.get("has_direct_route"))
            print("  count:           ", data.get("count"))
            print("  disclaimer:      ", data.get("disclaimer"))


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    print(f"Connecting to MCP server at {url} (streamable-http)...")
    anyio.run(run, url)


if __name__ == "__main__":
    main()
