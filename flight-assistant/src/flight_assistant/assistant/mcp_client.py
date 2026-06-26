"""Thin async wrapper around an MCP stdio client session.

The assistant uses *only* this client to reach route data. It spawns the MCP
server as a subprocess and talks to it over stdio — exactly how a host like
Claude Desktop or VS Code would. This keeps the assistant/data boundary honest.
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@asynccontextmanager
async def open_session(python_executable: str | None = None):
    """Open an initialized MCP ClientSession against the route-discovery server."""
    params = StdioServerParameters(
        command=python_executable or sys.executable,
        args=["-m", "flight_assistant.mcp_server.server"],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            yield session


def tool_result_to_dict(result: Any) -> dict:
    """Extract a plain dict from an MCP CallToolResult."""
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        # FastMCP wraps non-dict returns under a "result" key; unwrap if present.
        if set(structured.keys()) == {"result"}:
            return structured["result"]
        return structured

    # Fallback: parse the first text content block as JSON.
    content = getattr(result, "content", None) or []
    for block in content:
        text = getattr(block, "text", None)
        if text:
            import json

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"text": text}
    return {}
