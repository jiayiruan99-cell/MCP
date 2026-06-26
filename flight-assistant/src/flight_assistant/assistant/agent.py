"""The assistant/agent layer (LLM tool-calling over MCP).

The agent runs an OpenAI function-calling loop: it discovers the available tools
from the MCP session at runtime, lets the model decide which to call, executes
those calls over MCP, and feeds the structured results back until the model
produces a final answer.

The agent never imports the domain services or the data layer. It reaches route
data *only* through the MCP tool boundary, so adding a new tool on the server
requires no change here — it is advertised and used automatically.
"""

from __future__ import annotations

import json
import os

from ..config import load_config
from .mcp_client import open_session, tool_result_to_dict

load_config()

SYSTEM_PROMPT = (
    "You are a flight route-discovery assistant. You can ONLY answer using the "
    "provided tools. Never invent airports, airlines, or routes. The data is "
    "HISTORICAL OpenFlights connectivity data — it is not a live schedule, price, "
    "or booking source, and you must make that limitation clear (each tool result "
    "includes a 'disclaimer' you should respect). If no direct route exists, offer "
    "to look for one-stop alternatives. Keep answers concise and structured."
)


class MissingCredentialsError(RuntimeError):
    """Raised when the LLM backend is used without an API key configured."""


class Agent:
    """LLM agent that talks to the MCP route-discovery server."""

    def __init__(self, model: str | None = None, max_tool_turns: int = 6) -> None:
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
        self.max_tool_turns = max_tool_turns

    def _make_client(self):
        from openai import OpenAI  # imported lazily so it's only needed at runtime

        # OPENAI_BASE_URL lets you point at any OpenAI-compatible endpoint
        # (e.g. a local Ollama / LM Studio server) instead of OpenAI itself.
        base_url = os.environ.get("OPENAI_BASE_URL")
        if not os.environ.get("OPENAI_API_KEY") and not base_url:
            raise MissingCredentialsError(
                "No OPENAI_API_KEY set. Set it (or OPENAI_BASE_URL for a local "
                "OpenAI-compatible server) to run the assistant. The MCP server, "
                "tests, and MCP hosts (Claude/VS Code) work without a key."
            )
        return OpenAI(base_url=base_url) if base_url else OpenAI()

    async def answer(self, query: str) -> str:
        client = self._make_client()
        async with open_session() as session:
            return await self._run(client, session, query)

    async def _run(self, client, session, query: str) -> str:
        mcp_tools = (await session.list_tools()).tools
        oai_tools = [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.inputSchema,
                },
            }
            for t in mcp_tools
        ]

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ]

        for _ in range(self.max_tool_turns):
            resp = client.chat.completions.create(
                model=self.model, messages=messages, tools=oai_tools, temperature=0
            )
            msg = resp.choices[0].message
            if not msg.tool_calls:
                return msg.content or "(no answer)"

            messages.append(msg.model_dump(exclude_none=True))
            for call in msg.tool_calls:
                args = json.loads(call.function.arguments or "{}")
                result = await session.call_tool(call.function.name, args)
                data = tool_result_to_dict(result)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(data),
                    }
                )
        return "Stopped after too many tool calls; please rephrase your question."
