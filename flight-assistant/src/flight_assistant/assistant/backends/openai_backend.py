"""OpenAI (and OpenAI-compatible) LLM backend.

Works with OpenAI itself and any OpenAI-compatible endpoint (Azure OpenAI,
Groq, Together, local Ollama / LM Studio, vLLM, ...) via ``OPENAI_BASE_URL``.
"""

from __future__ import annotations

import json
import os
from typing import Any

from .base import LLMBackend, LLMResponse, MissingCredentialsError, ToolCall

# Default to OpenAI's EU regional endpoint (required for EU data-residency
# projects). Override via OPENAI_BASE_URL for the global endpoint or a local
# OpenAI-compatible server.
DEFAULT_BASE_URL = "https://eu.api.openai.com/v1"


class OpenAIBackend(LLMBackend):
    """Drives OpenAI's chat-completions function-calling API."""

    name = "openai"

    @property
    def default_model(self) -> str:
        return os.environ.get("OPENAI_MODEL", "gpt-4.1-nano")

    def make_client(self) -> Any:
        from openai import OpenAI  # imported lazily so it's only needed at runtime

        # OPENAI_BASE_URL lets you point at any OpenAI-compatible endpoint
        # (e.g. a local Ollama / LM Studio server). If unset, default to the EU
        # regional endpoint, which EU data-residency projects require.
        base_url = os.environ.get("OPENAI_BASE_URL") or DEFAULT_BASE_URL
        if not os.environ.get("OPENAI_API_KEY"):
            raise MissingCredentialsError(
                "No OPENAI_API_KEY set. Set it to run the assistant. The MCP "
                "server, tests, and MCP hosts (Claude/VS Code) work without a key."
            )
        return OpenAI(base_url=base_url)

    def build_tools(self, mcp_tools: list) -> Any:
        return [
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

    def initial_messages(self, system: str, user: str) -> list:
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def chat(self, client: Any, model: str, messages: list, tools: Any) -> LLMResponse:
        resp = client.chat.completions.create(
            model=model, messages=messages, tools=tools, temperature=0
        )
        msg = resp.choices[0].message
        calls = [
            ToolCall(
                id=c.id,
                name=c.function.name,
                arguments=json.loads(c.function.arguments or "{}"),
            )
            for c in (msg.tool_calls or [])
        ]
        return LLMResponse(text=msg.content, tool_calls=calls, raw=msg)

    def append_assistant(self, messages: list, response: LLMResponse) -> None:
        messages.append(response.raw.model_dump(exclude_none=True))

    def append_tool_result(self, messages: list, call: ToolCall, data: dict) -> None:
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(data),
            }
        )
