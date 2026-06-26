# Design notes, tradeoffs & next steps

## What was implemented

- Clean 4-layer separation with a hard MCP tool boundary.
- Per-capability vertical slices (`domain/<cap>` + `mcp_server/tools/<cap>`) behind a `ServiceRegistry`, so new capabilities are added without touching existing ones.
- 3 typed, independently-testable tools with an enforced data-limitation disclaimer.
- City / country / IATA / name resolution; direct routes; one-stop alternatives.
- LLM agent that discovers tools dynamically over MCP (adding a tool needs no agent change).

## Intentionally deferred (MVP scope)

- Live schedules, pricing, booking, payments, auth — not available in this phase.
- Multi-hop (>1 stop) routing and geo/time optimization.
- Persistent DB, caching tiers, rate limiting, fuzzy spelling correction.
- Full evaluation harness.

## How it evolves beyond route search

- Add new capabilities as _separate MCP servers / services_ (pricing, booking,
  schedules), keeping each tool boundary typed and independently testable.
- Synchronous tool calls fit request/response lookups today; move long-running
  or cross-service workflows to **events/queues** and **agent-to-agent (A2A)**
  messaging as specialized agents emerge.
- The assistant becomes an orchestrator over multiple tool/service boundaries.

## What production-readiness needs

- Observability: per-tool tracing, metrics, structured logs at the boundary.
- Security: authN/authZ on tools, input validation, rate limiting, PII handling.
- Reliability/scale: stateless tool servers, caching, health checks, graceful
  degradation; scheduled dataset refresh + freshness metadata.
- Quality: contract tests per tool, golden-query eval set, regression checks.
