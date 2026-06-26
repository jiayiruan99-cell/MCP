"""Async MCP client over the streamable-HTTP transport.

The assistant reaches route data *only* through this client. It launches the
MCP server as a local subprocess speaking **streamable HTTP**, then connects to
it over HTTP — the same transport a remote MCP host (e.g. a ChatGPT / Claude
connector) would use. Auto-starting the server keeps the CLI a single command
while still exercising the networked tool boundary end-to-end.
"""

from __future__ import annotations

import asyncio
import os
import socket
import sys
from contextlib import asynccontextmanager
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# How long to wait for the freshly-spawned server to start accepting connections.
_READY_TIMEOUT = 30.0


def _free_port() -> int:
    """Pick an available localhost TCP port for the server subprocess."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


async def _wait_until_ready(proc, host: str, port: int, timeout: float) -> None:
    """Block until the server accepts TCP connections, or raise on failure."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while True:
        if proc.returncode is not None:
            raise RuntimeError(
                f"MCP server exited early (code {proc.returncode}) before "
                "accepting connections."
            )
        try:
            _, writer = await asyncio.open_connection(host, port)
            writer.close()
            await writer.wait_closed()
            return
        except OSError:
            if loop.time() >= deadline:
                raise TimeoutError(
                    f"MCP server did not become ready on {host}:{port} "
                    f"within {timeout:.0f}s."
                )
            await asyncio.sleep(0.1)


@asynccontextmanager
async def open_session(host: str = "127.0.0.1", port: int | None = None):
    """Launch the MCP server over HTTP and yield an initialized session.

    Spawns ``flight_assistant.mcp_server.server`` with the streamable-HTTP
    transport on a local port, waits until it is listening, connects over HTTP,
    and terminates the subprocess on exit. The server's own logs are suppressed
    to keep the assistant output clean.
    """
    port = port or _free_port()
    env = {
        **os.environ,
        "MCP_TRANSPORT": "streamable-http",
        "MCP_HOST": host,
        "MCP_PORT": str(port),
    }
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "flight_assistant.mcp_server.server",
        env=env,
        stdout=asyncio.subprocess.DEVNULL,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        await _wait_until_ready(proc, host, port, _READY_TIMEOUT)
        url = f"http://{host}:{port}/mcp"
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                yield session
    finally:
        if proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()


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
