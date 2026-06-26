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
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

The OpenFlights datasets are downloaded and cached to `./data/` automatically on
first run.

---

## Run the assistant

The assistant uses an LLM (OpenAI function-calling) to orchestrate the MCP tools,
so it needs an API key. The CLI auto-starts the MCP server over streamable HTTP,
connects to it, and shuts it down on exit. (The MCP server, the tests, and MCP
hosts work **without a key**.)

```bash
export OPENAI_API_KEY=sk-...

flight-assistant "Can I fly from Berlin to Lisbon directly?"
flight-assistant --demo                       # scripted demo queries
flight-assistant                              # interactive REPL
```

---

## Tests

```bash
pytest
```

Tests run against a tiny inline dataset (no network, no API key) and cover
parsing, indexing, route discovery, and the disclaimer contract.

---

## Documentation

- [Architecture](docs/architecture.md) — layers, capability slices, and the tool contract.
- [Configuration](docs/configuration.md) — `.env` and environment variables.
- [Switching the model](docs/models.md) — OpenAI, Ollama (free/local), and self-hosting (vLLM).
- [MCP server & host setup](docs/mcp-server.md) — run standalone, serve over HTTP/SSE, attach a host.
- [Design notes & next steps](docs/design-notes.md) — tradeoffs, deferred scope, production-readiness.
