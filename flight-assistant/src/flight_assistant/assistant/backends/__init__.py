"""LLM backend registry.

Selects a provider-specific :class:`LLMBackend` by name (default: the
``LLM_PROVIDER`` environment variable, falling back to ``"openai"``).

Adding a provider is two steps: implement ``LLMBackend`` in a sibling module,
then register its factory in ``_BACKENDS`` below — no agent change required.
"""

from __future__ import annotations

import os
from typing import Callable

from .base import LLMBackend, LLMResponse, MissingCredentialsError, ToolCall
from .openai_backend import OpenAIBackend

# Map provider name -> zero-arg factory. Keep factories lazy so importing a
# provider's SDK only happens when that provider is actually selected.
_BACKENDS: dict[str, Callable[[], LLMBackend]] = {
    "openai": OpenAIBackend,
}


def get_backend(name: str | None = None) -> LLMBackend:
    """Return an LLM backend instance for ``name`` (or ``$LLM_PROVIDER``)."""
    key = (name or os.environ.get("LLM_PROVIDER", "openai")).lower()
    try:
        factory = _BACKENDS[key]
    except KeyError:
        known = ", ".join(sorted(_BACKENDS))
        raise ValueError(f"Unknown LLM provider '{key}'. Known providers: {known}.")
    return factory()


__all__ = [
    "LLMBackend",
    "LLMResponse",
    "MissingCredentialsError",
    "ToolCall",
    "get_backend",
]
