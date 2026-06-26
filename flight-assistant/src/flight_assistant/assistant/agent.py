"""The assistant/agent layer (LLM tool-calling over MCP).

The agent runs a *provider-neutral* function-calling loop: it discovers the
available tools from the MCP session at runtime, lets the model decide which to
call, executes those calls over MCP, and feeds the structured results back until
the model produces a final answer.

Everything specific to a particular LLM SDK lives behind an
:class:`~flight_assistant.assistant.backends.base.LLMBackend` (see the
``backends/`` package), selected via the ``LLM_PROVIDER`` env var. Switching
providers therefore requires no change to this loop.

The agent never imports the domain services or the data layer. It reaches route
data *only* through the MCP tool boundary, so adding a new tool on the server
requires no change here — it is advertised and used automatically.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from ..config import load_config
from .backends import MissingCredentialsError, get_backend
from .mcp_client import open_session, tool_result_to_dict

load_config()

SYSTEM_PROMPT = (
    "You are a flight route-discovery assistant. You can ONLY answer using the "
    "provided tools. Never invent airports, airlines, or routes. The data is "
    "HISTORICAL OpenFlights connectivity data — it is not a live schedule, price, "
    "or booking source. If no direct route exists, offer to look for one-stop "
    "alternatives. Keep answers concise and structured. Do NOT write your own "
    "data-limitation disclaimer — the application appends the official disclaimer "
    "automatically, so adding one yourself would duplicate it."
)

__all__ = ["Agent", "MissingCredentialsError"]


def _append_disclaimers(answer: str, disclaimers: list[str]) -> str:
    """Deterministically append tool disclaimers to the model's answer.

    Enforcement lives here, not in the prompt: the model is non-deterministic
    and may omit the caveat, so we always append the exact disclaimer text
    carried by the tool results that were actually used. Each distinct
    disclaimer is added once; any already present in the answer is skipped.
    """
    footer = [d for d in dict.fromkeys(disclaimers) if d and d not in answer]
    if not footer:
        return answer
    return answer.rstrip() + "\n\n" + "\n".join(f"⚠️  {d}" for d in footer)


class Agent:
    """LLM agent that talks to the MCP route-discovery server.

    The LLM provider is pluggable via ``provider`` (or the ``LLM_PROVIDER`` env
    var); the orchestration loop itself is provider-agnostic.
    """

    def __init__(
        self,
        model: str | None = None,
        max_tool_turns: int = 6,
        provider: str | None = None,
    ) -> None:
        self.backend = get_backend(provider)
        self.model = model or self.backend.default_model
        self.max_tool_turns = max_tool_turns
        self._client = None
        self._session = None

    @asynccontextmanager
    async def connect(self):
        """Open one MCP session (one server subprocess) for multiple queries.

        The server loads the OpenFlights datasets once on first use and caches
        them via the ServiceRegistry, so reusing this session across queries
        avoids reloading the data for every question.
        """
        client = self.backend.make_client()
        async with open_session() as session:
            self._client, self._session = client, session
            try:
                yield self
            finally:
                self._client, self._session = None, None

    async def answer(self, query: str) -> str:
        # Reuse an open session if we're inside `connect()`; otherwise open a
        # one-shot session for this single query.
        if self._session is not None:
            return await self._run(self._client, self._session, query)
        client = self.backend.make_client()
        async with open_session() as session:
            return await self._run(client, session, query)

    async def _run(self, client, session, query: str) -> str:
        mcp_tools = (await session.list_tools()).tools
        tools = self.backend.build_tools(mcp_tools)
        messages = self.backend.initial_messages(SYSTEM_PROMPT, query)

        # Disclaimers carried by the tool results actually used this turn. We
        # append these deterministically so the caveat never depends on the LLM.
        disclaimers: list[str] = []

        for _ in range(self.max_tool_turns):
            response = self.backend.chat(client, self.model, messages, tools)
            if not response.tool_calls:
                answer = response.text or "(no answer)"
                return _append_disclaimers(answer, disclaimers)

            self.backend.append_assistant(messages, response)
            for call in response.tool_calls:
                result = await session.call_tool(call.name, call.arguments)
                data = tool_result_to_dict(result)
                disclaimer = data.get("disclaimer") if isinstance(data, dict) else None
                if disclaimer:
                    disclaimers.append(disclaimer)
                self.backend.append_tool_result(messages, call, data)

        return "Stopped after too many tool calls; please rephrase your question."
