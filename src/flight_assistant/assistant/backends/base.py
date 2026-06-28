"""Provider-neutral LLM backend interface.

The :class:`~flight_assistant.assistant.agent.Agent` runs a provider-agnostic
function-calling loop. Everything that differs between LLM SDKs (OpenAI,
Anthropic, Gemini, ...) is isolated behind :class:`LLMBackend`:

* how to build a client,
* how to translate MCP tool schemas into the provider's tool format,
* how to seed and grow the conversation,
* how to make one chat turn and read its result.

To add a new provider, implement ``LLMBackend`` in a sibling module and register
it in ``backends/__init__.py`` — no change to the agent loop is required.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


class MissingCredentialsError(RuntimeError):
    """Raised when a backend is used without the required credentials."""


@dataclass
class ToolCall:
    """A provider-neutral request from the model to invoke an MCP tool."""

    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    """The outcome of one chat turn, normalized across providers.

    If ``tool_calls`` is empty, ``text`` holds the final answer. Otherwise the
    model wants to call tools, and ``raw`` carries the provider's original
    assistant message so the backend can append it back to the conversation.
    """

    text: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: Any = None


@runtime_checkable
class LLMBackend(Protocol):
    """Everything provider-specific about driving an LLM tool-calling loop."""

    #: Human-readable provider name (e.g. "openai").
    name: str

    @property
    def default_model(self) -> str:
        """Model used when none is given via CLI/env."""

    def make_client(self) -> Any:
        """Create the provider SDK client (raising MissingCredentialsError)."""

    def build_tools(self, mcp_tools: list) -> Any:
        """Translate MCP tool definitions into the provider's tool schema."""

    def initial_messages(self, system: str, user: str) -> list:
        """Seed the conversation with the system prompt and user query."""

    def append_user(self, messages: list, user: str) -> None:
        """Append a follow-up user turn to an ongoing conversation."""

    def chat(self, client: Any, model: str, messages: list, tools: Any) -> LLMResponse:
        """Run one chat turn and normalize the result to LLMResponse."""

    def append_assistant(self, messages: list, response: LLMResponse) -> None:
        """Append the assistant's tool-calling message to the conversation."""

    def append_assistant_text(self, messages: list, text: str) -> None:
        """Append the assistant's final text answer to the conversation."""

    def append_tool_result(self, messages: list, call: ToolCall, data: dict) -> None:
        """Append the result of one tool call to the conversation."""
