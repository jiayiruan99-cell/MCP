"""Tests for the deterministic disclaimer enforcement in the agent layer.

These verify the application *always* appends tool disclaimers regardless of
what the LLM produced. They are token-free: they call the pure helper directly
and never touch the network or an API key.
"""

from __future__ import annotations

from flight_assistant.assistant.agent import _append_disclaimers

DISCLAIMER = "Historical data only. Verify before travel."
OTHER = "Pricing is indicative, not a quote."


def test_appends_disclaimer_when_missing():
    out = _append_disclaimers("Berlin to Lisbon is direct.", [DISCLAIMER])
    assert DISCLAIMER in out
    assert out.startswith("Berlin to Lisbon is direct.")
    assert "⚠️" in out


def test_no_disclaimers_leaves_answer_untouched():
    answer = "Just a friendly hello."
    assert _append_disclaimers(answer, []) == answer


def test_does_not_duplicate_when_already_present():
    answer = f"Some answer.\n\n{DISCLAIMER}"
    out = _append_disclaimers(answer, [DISCLAIMER])
    assert out.count(DISCLAIMER) == 1


def test_dedupes_repeated_disclaimers():
    out = _append_disclaimers("Answer.", [DISCLAIMER, DISCLAIMER])
    assert out.count(DISCLAIMER) == 1


def test_appends_multiple_distinct_disclaimers():
    out = _append_disclaimers("Answer.", [DISCLAIMER, OTHER])
    assert DISCLAIMER in out
    assert OTHER in out


def test_ignores_empty_disclaimer_strings():
    out = _append_disclaimers("Answer.", ["", DISCLAIMER, ""])
    assert out.count("⚠️") == 1
    assert DISCLAIMER in out
