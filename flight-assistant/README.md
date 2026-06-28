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

## Setup

Requires Python 3.10+.

```bash
cd flight-assistant
python3 -m venv .venv        # Windows: py -m venv .venv
source .venv/bin/activate    # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

---

## Run the assistant

The assistant uses an LLM (OpenAI function-calling) to orchestrate the MCP tools,
so it needs an API key. Copy `.env.example` to `.env` and set your key — it's
loaded automatically on all platforms:

```bash
flight-assistant "Can I fly from Berlin to Lisbon directly?"
flight-assistant --demo      # scripted demo queries
flight-assistant             # interactive REPL
```

The CLI auto-starts the MCP server over streamable HTTP, connects, and shuts it
down on exit. The MCP server, the tests, and MCP hosts work **without a key**.

---

## Tests

```bash
pytest
```

Tests use a tiny inline dataset (no network, no API key) covering parsing,
indexing, route discovery, and the disclaimer contract.

---

## Note on Architecture, tradeoffs and next steps:

[Architecture](docs/architecture.md)

## Other Documentation

- [Configuration](docs/configuration.md) — `.env` and environment variables.
- [Switching the model](docs/models.md) — OpenAI, Ollama (free/local), and self-hosting (vLLM).
- [MCP server & host setup](docs/mcp-server.md) — run standalone, serve over HTTP/SSE, attach a host.
