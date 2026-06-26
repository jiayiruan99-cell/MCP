# Architecture

```
┌──────────────────────────┐
│  Assistant / Agent layer │  natural language ⇄ tool calls
│  (LLM agent)             │  — never touches data directly
└─────────────┬────────────┘
              │  MCP protocol (streamable HTTP)
┌─────────────▼────────────┐
│   MCP server (tools)     │  find_airports
│   integration boundary   │  find_direct_routes
│                          │  suggest_alternative_routes
└─────────────┬────────────┘
              │  Python calls
┌─────────────▼────────────┐
│  Route discovery domain  │  pure, typed, unit-testable logic
│  service                 │
└─────────────┬────────────┘
              │
┌─────────────▼────────────┐
│  Data access layer       │  the ONLY layer that touches
│  (loader + repository)   │  the network / filesystem
└──────────────────────────┘
```

**Key boundary rule:** the assistant interacts with route data _only_ through
the MCP tools. It never loads files, queries datasets, or calls external
systems. The data layer is the single place that performs I/O.

## Layers

| Layer         | Module                                 | Responsibility                                                            |
| ------------- | -------------------------------------- | ------------------------------------------------------------------------- |
| Data access   | `flight_assistant.data_access`         | Download/cache `.dat` files, parse, build in-memory indexes.              |
| Domain        | `flight_assistant.domain.<capability>` | Per-capability logic + typed tool I/O models (each carries a disclaimer). |
| Tool boundary | `flight_assistant.mcp_server`          | MCP server + registry exposing each capability's tools.                   |
| Assistant     | `flight_assistant.assistant`           | LLM agent orchestration; only talks to MCP tools.                         |

## Capability slices (designed for extension)

Each capability is a self-contained vertical slice with matching files on both
sides of the boundary. Adding a capability means adding a new slice + tool module
and registering it — **existing capabilities are untouched**.

```
domain/
├── base.py                 # ToolResult base + shared disclaimer
├── airports/               # AirportInfo, FindAirportsResult, AirportService
└── routes/                 # Route/Connection models, RouteDiscoveryService

mcp_server/
├── server.py               # thin: loops over CAPABILITY_MODULES and registers
├── registry.py             # ServiceRegistry: loads data once, lazy services
└── tools/
    ├── airports.py         # register(mcp, registry) -> find_airports
    └── routes.py           # register(...) -> find_direct_routes, suggest_alternative_routes
```

## The tool contract

| Tool                         | Inputs                                              | Returns                                                |
| ---------------------------- | --------------------------------------------------- | ------------------------------------------------------ |
| `find_airports`              | `query: str`, `limit: int = 10`                     | Airports matching a city, country, IATA code, or name. |
| `find_direct_routes`         | `origin: str`, `destination: str`                   | Historical non-stop routes + operating airlines.       |
| `suggest_alternative_routes` | `origin: str`, `destination: str`, `limit: int = 5` | One-stop `origin → hub → destination` itineraries.     |

Inputs/outputs are typed with Pydantic, so the schemas are auto-advertised over
MCP and are independently testable.
