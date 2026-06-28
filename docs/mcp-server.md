# Running the MCP server & attaching a host

## Run the server standalone

The **server supports both transports**. `stdio` is the default and is what
local MCP hosts (Claude Desktop / VS Code) use; `streamable-http` is for remote
connectors. (Note: the in-repo `flight-assistant` CLI always talks to the server
over HTTP — it auto-starts its own server — but the standalone server below is
fully usable over stdio for any MCP host.)

```bash
flight-mcp-server          # serves over stdio (default transport)
# or inspect interactively:
mcp dev src/flight_assistant/mcp_server/server.py
```

### Serving over HTTP/SSE (remote connector)

For a **remote** deployment — e.g. hosting the server as a shared connector for
ChatGPT / Claude Team, or behind a load balancer — switch the transport to
streamable HTTP via `MCP_TRANSPORT`. The tools, registry, domain, and data
layers are **unchanged**; only the transport differs.

```bash
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 flight-mcp-server
# endpoint: POST http://<host>:8000/mcp   (use MCP_TRANSPORT=sse for legacy SSE)
```

The HTTP/SSE transports bind to `127.0.0.1` by default; set `MCP_HOST=0.0.0.0`
to accept external connections. **In any real deployment, never expose the raw
port** — front it with TLS + auth (API gateway / reverse proxy / org SSO), since
the MCP server itself does not authenticate callers.

## Attaching a host

An MCP **host** (Claude Desktop, VS Code, ChatGPT/Claude connectors, or your own
client) connects to the server over one of the two transports. Pick based on
whether the host runs locally or remotely.

### A. Local host over stdio (Claude Desktop / VS Code)

The host launches the server as a subprocess and speaks stdio — no port, no
network. Point the host's MCP config at the installed entry point:

```json
{
  "mcpServers": {
    "flight-route-discovery": {
      "command": "/absolute/path/flight-assistant/.venv/bin/flight-mcp-server"
    }
  }
}
```

That's it — restart the host and the three tools (`find_airports`,
`find_direct_routes`, `suggest_alternative_routes`) appear. No `OPENAI_API_KEY`
is needed; the host supplies its own model.

### B. Remote host over streamable HTTP (ChatGPT / Claude connectors)

For a host that attaches over the network, run the server with the HTTP
transport and register its URL as a connector:

```bash
# 1. Start the server over HTTP (front with TLS + auth in real deployments)
MCP_TRANSPORT=http MCP_HOST=0.0.0.0 MCP_PORT=8000 flight-mcp-server

# 2. Attach the host to the endpoint:
#    https://<your-host>/mcp     (locally: http://127.0.0.1:8000/mcp)
```

Most remote MCP hosts (ChatGPT/Claude Team connectors) ask for the **server
URL** ending in `/mcp`. The server does **not** authenticate callers itself, so
for anything beyond localhost put it behind TLS + auth (API gateway / reverse
proxy / org SSO).

To verify the HTTP endpoint before attaching a real host, use the example
client (it does the initialize → list-tools → call-tool handshake):

```bash
python examples/http_client_demo.py http://127.0.0.1:8000/mcp
```
