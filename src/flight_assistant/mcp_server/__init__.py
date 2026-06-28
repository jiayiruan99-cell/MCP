"""MCP server package: the route-discovery tool boundary.

The server module is intentionally not imported here. It is executed as a script
(``python -m flight_assistant.mcp_server.server``), so eagerly importing it would
trigger a double-import RuntimeWarning.
"""
