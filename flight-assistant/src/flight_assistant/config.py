"""Centralized configuration loading.

Loads environment variables from a ``.env`` file (if present) exactly once, so
all entry points (CLI, MCP server) share the same config source. Real OS
environment variables always take precedence over ``.env`` values.

Recognized variables:
  * OPENAI_API_KEY   – enables the LLM backend when set.
  * OPENAI_MODEL     – model name for the LLM backend (default: gpt-4.1-nano).
  * OPENAI_BASE_URL  – optional; point at any OpenAI-compatible endpoint
                       (e.g. a local Ollama / LM Studio server).
  * LOG_LEVEL        – logging level for the MCP server (default: INFO).
  * OPENFLIGHTS_DATA_DIR – optional override for the dataset cache directory.
"""

from __future__ import annotations

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def load_config() -> None:
    """Load variables from a ``.env`` file into the process environment once.

    Safe to call from every entry point; the ``lru_cache`` guarantees the file
    is only read a single time per process. If ``python-dotenv`` is not
    installed, this is a no-op and plain OS environment variables are used.
    """
    try:
        from dotenv import load_dotenv
    except ImportError:
        return

    # override=False -> real environment variables win over .env entries.
    load_dotenv(dotenv_path=_find_dotenv(), override=False)


def _find_dotenv() -> str | None:
    """Locate a ``.env`` file: explicit DOTENV_PATH, else nearest walking up."""
    explicit = os.environ.get("DOTENV_PATH")
    if explicit:
        return explicit

    from pathlib import Path

    here = Path.cwd()
    for directory in (here, *here.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            return str(candidate)
    return None
