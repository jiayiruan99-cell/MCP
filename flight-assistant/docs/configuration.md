# Configuration

The assistant uses an LLM (OpenAI function-calling) to orchestrate the MCP tools,
so it needs an API key. The **MCP server, the tests, and MCP hosts** (Claude /
VS Code) all work **without a key**.

## `.env` (optional)

Instead of exporting variables, copy `.env.example` to `.env` and edit it — it
is loaded automatically (real OS env vars still take precedence). The `.env`
file is git-ignored.

```bash
cp .env.example .env
# then edit .env
```

| Variable               | Purpose                                                         | Default                                                   |
| ---------------------- | --------------------------------------------------------------- | --------------------------------------------------------- |
| `OPENAI_API_KEY`       | Required to run the assistant (LLM agent).                      | _(unset → assistant errors out; server/tests still work)_ |
| `LLM_PROVIDER`         | LLM backend to use (see [Switching the model](models.md)).      | `openai`                                                  |
| `OPENAI_MODEL`         | Model for the LLM agent.                                        | `gpt-4.1-nano`                                            |
| `OPENAI_BASE_URL`      | OpenAI-compatible endpoint (e.g. local Ollama/LM Studio).       | OpenAI EU endpoint                                        |
| `MCP_TRANSPORT`        | MCP server transport: `stdio`, `streamable-http`/`http`, `sse`. | `stdio`                                                   |
| `MCP_HOST`             | Bind address for the HTTP/SSE transports.                       | `127.0.0.1`                                               |
| `MCP_PORT`             | Port for the HTTP/SSE transports.                               | `8000`                                                    |
| `LOG_LEVEL`            | MCP server log level.                                           | `INFO`                                                    |
| `OPENFLIGHTS_DATA_DIR` | Dataset cache directory.                                        | `./data`                                                  |
