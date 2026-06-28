"""Assistant layer: LLM/agent orchestration over the MCP tool boundary."""

from .agent import Agent, MissingCredentialsError

__all__ = ["Agent", "MissingCredentialsError"]
