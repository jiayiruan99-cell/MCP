"""Domain layer: pure capability logic and the typed tool contract.

Each capability is a self-contained vertical slice under its own subpackage
(``airports``, ``routes``, ...). Adding a new capability means adding a new
slice here plus a matching tool module in ``flight_assistant.mcp_server.tools``
— existing capabilities are untouched.
"""

from .base import OPENFLIGHTS_DISCLAIMER, ToolResult

__all__ = ["OPENFLIGHTS_DISCLAIMER", "ToolResult"]
