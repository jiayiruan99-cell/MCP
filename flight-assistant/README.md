# Flight Route Discovery Assistant

A conversational assistant that answers natural-language flight-route questions
(e.g. _"Can I fly from Berlin to Lisbon directly?"_) over the public
[OpenFlights](https://openflights.org/data.php) airport, airline, and route
datasets — exposed to the assistant through a clean **MCP (Model Context
Protocol)** tool boundary.

> ⚠️ **Data limitation:** OpenFlights route data is _historical connectivity_,
> not a live schedule. It does not reflect current availability, timings,
> pricing, or bookings. Every tool response carries an explicit `disclaimer`
> field, and the assistant is instructed to surface it.

---

## Architecture

```
┌──────────────────────────┐
│  Assistant / Agent layer │  natural language ⇄ tool calls
│  (LLM agent)             │  — never touches data directly
└─────────────┬────────────┘
              │  MCP protocol (stdio)
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

### Layers

| Layer         | Module                                 | Responsibility                                                            |
| ------------- | -------------------------------------- | ------------------------------------------------------------------------- |
| Data access   | `flight_assistant.data_access`         | Download/cache `.dat` files, parse, build in-memory indexes.              |
| Domain        | `flight_assistant.domain.<capability>` | Per-capability logic + typed tool I/O models (each carries a disclaimer). |
| Tool boundary | `flight_assistant.mcp_server`          | MCP server + registry exposing each capability's tools.                   |
| Assistant     | `flight_assistant.assistant`           | LLM agent orchestration; only talks to MCP tools.                         |

### Capability slices (designed for extension)

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

---

## The tool contract

| Tool                         | Inputs                                              | Returns                                                |
| ---------------------------- | --------------------------------------------------- | ------------------------------------------------------ |
| `find_airports`              | `query: str`, `limit: int = 10`                     | Airports matching a city, country, IATA code, or name. |
| `find_direct_routes`         | `origin: str`, `destination: str`                   | Historical non-stop routes + operating airlines.       |
| `suggest_alternative_routes` | `origin: str`, `destination: str`, `limit: int = 5` | One-stop `origin → hub → destination` itineraries.     |

Inputs/outputs are typed with Pydantic, so the schemas are auto-advertised over
MCP and are independently testable.

---

## Setup

Requires Python 3.10+.

```bash
cd flight-assistant
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The OpenFlights datasets are downloaded and cached to `./data/` automatically on
first run.

---

## Running

The assistant uses an LLM (OpenAI function-calling) to orchestrate the MCP tools,
so it needs an API key. The **MCP server, the tests, and MCP hosts** (Claude /
VS Code) all work **without a key**.

### 1. Talk to the assistant

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_MODEL=gpt-4.1-nano               # optional, see “Switching the model”

flight-assistant "Can I fly from Berlin to Lisbon directly?"
flight-assistant --demo                       # scripted demo queries
flight-assistant                              # interactive REPL
```

#### Configuration via `.env` (optional)

Instead of exporting variables, copy `.env.example` to `.env` and edit it — it
is loaded automatically (real OS env vars still take precedence). The `.env`
file is git-ignored.

```bash
cp .env.example .env
# then edit .env
```

| Variable               | Purpose                                                   | Default                                                   |
| ---------------------- | --------------------------------------------------------- | --------------------------------------------------------- |
| `OPENAI_API_KEY`       | Required to run the assistant (LLM agent).                | _(unset → assistant errors out; server/tests still work)_ |
| `LLM_PROVIDER`         | LLM backend to use (see “Switching the model” below).     | `openai`                                                  |
| `OPENAI_MODEL`         | Model for the LLM agent.                                  | `gpt-4.1-nano`                                            |
| `OPENAI_BASE_URL`      | OpenAI-compatible endpoint (e.g. local Ollama/LM Studio). | OpenAI EU endpoint                                        |
| `LOG_LEVEL`            | MCP server log level.                                     | `INFO`                                                    |
| `OPENFLIGHTS_DATA_DIR` | Dataset cache directory.                                  | `./data`                                                  |

#### Switching the model

The agent depends on an `LLMBackend` interface, not a specific vendor, so most
switches are pure configuration. There are three tiers:

**1. Different OpenAI model — config only.**

```bash
export OPENAI_MODEL=gpt-4o-mini          # or via .env / --model
flight-assistant --model gpt-4o "from Tokyo to Reykjavik"
```

`--model` overrides `OPENAI_MODEL` for a single run, which is handy for A/B
comparisons (the CLI prints end-to-end latency per query).

**2. Different OpenAI-compatible provider — config only.**

Any endpoint that speaks the OpenAI API (Azure OpenAI, Groq, Together, local
Ollama / LM Studio, vLLM, …) works by pointing `OPENAI_BASE_URL` at it:

```bash
# Local Ollama (free, no real token needed — great for token-free demos)
export OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_MODEL=llama3.1
export OPENAI_API_KEY=ollama            # dummy, just must be non-empty

# Groq
export OPENAI_BASE_URL=https://api.groq.com/openai/v1
export OPENAI_MODEL=llama-3.1-8b-instant
```

No code changes — the OpenAI backend already reads `OPENAI_BASE_URL`.

**3. A different SDK (e.g. Anthropic Claude, Google Gemini) — one new file.**

Providers with their own SDKs/message formats are isolated behind the
`LLMBackend` interface in [`assistant/backends/`](src/flight_assistant/assistant/backends).
To add one:

1. Implement `LLMBackend` in `assistant/backends/<provider>_backend.py`.
2. Register it in `assistant/backends/__init__.py` (`_BACKENDS`).
3. Select it with `LLM_PROVIDER=<provider>` or `--provider <provider>`.

The agent loop, MCP server, tools, registry, domain, and data layers are
**unchanged** — only the new backend file is added.

### 2. Run the MCP server standalone

```bash
flight-mcp-server          # serves over stdio
# or inspect interactively:
mcp dev src/flight_assistant/mcp_server/server.py
```

### 3. Wire into an MCP host (e.g. Claude Desktop / VS Code)

```json
{
  "mcpServers": {
    "flight-route-discovery": {
      "command": "/absolute/path/flight-assistant/.venv/bin/flight-mcp-server"
    }
  }
}
```

---

## Tests

```bash
pytest
```

Tests run against a tiny inline dataset (no network, no API key) and cover
parsing, indexing, route discovery, and the disclaimer contract. Each capability
has its own test module (`test_airports.py`, `test_routes.py`).

---

## Design notes, tradeoffs & next steps

**What was implemented**

- Clean 4-layer separation with a hard MCP tool boundary.
- Per-capability vertical slices (`domain/<cap>` + `mcp_server/tools/<cap>`) behind a `ServiceRegistry`, so new capabilities are added without touching existing ones.
- 3 typed, independently-testable tools with an enforced data-limitation disclaimer.
- City / country / IATA / name resolution; direct routes; one-stop alternatives.
- LLM agent that discovers tools dynamically over MCP (adding a tool needs no agent change).

**Intentionally deferred (MVP scope)**

- Live schedules, pricing, booking, payments, auth — not available in this phase.
- Multi-hop (>1 stop) routing and geo/time optimization.
- Persistent DB, caching tiers, rate limiting, fuzzy spelling correction.
- Full evaluation harness.

**How it evolves beyond route search**

- Add new capabilities as _separate MCP servers / services_ (pricing, booking,
  schedules), keeping each tool boundary typed and independently testable.
- Synchronous tool calls fit request/response lookups today; move long-running
  or cross-service workflows to **events/queues** and **agent-to-agent (A2A)**
  messaging as specialized agents emerge.
- The assistant becomes an orchestrator over multiple tool/service boundaries.

**What production-readiness needs**

- Observability: per-tool tracing, metrics, structured logs at the boundary.
- Security: authN/authZ on tools, input validation, rate limiting, PII handling.
- Reliability/scale: stateless tool servers, caching, health checks, graceful
  degradation; scheduled dataset refresh + freshness metadata.
- Quality: contract tests per tool, golden-query eval set, regression checks.
