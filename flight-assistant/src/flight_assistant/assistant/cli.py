"""Command-line entry point for the flight route-discovery assistant.

Usage:
    flight-assistant "Can I fly from Berlin to Lisbon directly?"
    flight-assistant            # interactive REPL
    flight-assistant --demo     # run a scripted set of demo queries

The CLI launches the MCP server over streamable HTTP via the agent's MCP client
and uses an LLM (OpenAI function-calling) to orchestrate the tools. Set
``OPENAI_API_KEY`` (or ``OPENAI_BASE_URL`` for a local OpenAI-compatible server)
to run it. The MCP server, tests, and MCP hosts work without a key.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time

from .agent import Agent, MissingCredentialsError


def _leaf_errors(exc: BaseException) -> list[BaseException]:
    """Flatten an ExceptionGroup into its underlying leaf exceptions.

    The MCP client runs inside an anyio task group, so a failure there is
    re-raised as an ``ExceptionGroup`` whose message is the unhelpful
    "unhandled errors in a TaskGroup". Unwrapping it surfaces the real cause
    (e.g. an OpenAI auth/network error) to the user.
    """
    inner = getattr(exc, "exceptions", None)
    if inner:
        leaves: list[BaseException] = []
        for sub in inner:
            leaves.extend(_leaf_errors(sub))
        return leaves
    return [exc]

DEMO_QUERIES = [
    "Can I fly from Berlin to Lisbon directly?",
    "Find airports in Portugal",
    "What is airport BER?",
    "from Tokyo to Reykjavik",  # likely no direct route -> alternatives
    "alternatives from Berlin to New York",
]


async def _run_once(agent: Agent, query: str) -> float:
    """Answer one query, printing the result and its end-to-end latency.

    Returns the elapsed wall-clock time in seconds.
    """
    print(f"\n\033[1m▶ {query}\033[0m")
    start = time.perf_counter()
    answer = await agent.answer(query)
    elapsed = time.perf_counter() - start
    print(answer)
    print(
        f"\033[2m⏱  {elapsed:.2f}s end-to-end · "
        f"{agent.last_tool_rounds} tool round(s), "
        f"{agent.last_tool_calls} tool call(s)\033[0m"
    )
    return elapsed

# Read–Eval–Print Loop
async def _repl(agent: Agent) -> None:
    print("Flight route-discovery assistant. Type a question, or 'quit' to exit.\n")
    async with agent.connect():
        while True:
            try:
                query = input("you › ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if query.lower() in {"quit", "exit", "q"}:
                break
            if not query:
                continue
            start = time.perf_counter()
            answer = await agent.answer(query)
            elapsed = time.perf_counter() - start
            print(answer)
            print(
                f"\033[2m⏱  {elapsed:.2f}s end-to-end · "
                f"{agent.last_tool_rounds} tool round(s), "
                f"{agent.last_tool_calls} tool call(s)\033[0m\n"
            )


async def _demo(agent: Agent) -> None:
    print("Running demo queries")
    timings = []
    async with agent.connect():
        for q in DEMO_QUERIES:
            timings.append(await _run_once(agent, q))
    total = sum(timings)
    avg = total / len(timings) if timings else 0.0
    print(
        f"\n\033[1mDemo complete:\033[0m {len(timings)} queries in "
        f"{total:.2f}s (avg {avg:.2f}s/query)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight route-discovery assistant")
    parser.add_argument("query", nargs="*", help="A natural-language route question.")
    parser.add_argument("--demo", action="store_true", help="Run scripted demo queries.")
    parser.add_argument(
        "--model", help="Override the LLM model (default: OPENAI_MODEL or gpt-5.4-nano)."
    )
    parser.add_argument(
        "--provider", help="LLM provider backend (default: LLM_PROVIDER or 'openai')."
    )
    args = parser.parse_args()

    agent = Agent(model=args.model, provider=args.provider)

    try:
        if args.demo:
            asyncio.run(_demo(agent))
        elif args.query:
            asyncio.run(_run_once(agent, " ".join(args.query)))
        else:
            asyncio.run(_repl(agent))
    except MissingCredentialsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2)
    except Exception as exc:  # noqa: BLE001 - surface LLM/API errors cleanly
        # anyio wraps task-group failures in an ExceptionGroup ("unhandled
        # errors in a TaskGroup"); unwrap it so the real cause is shown.
        for leaf in _leaf_errors(exc):
            if isinstance(leaf, MissingCredentialsError):
                print(f"error: {leaf}", file=sys.stderr)
                raise SystemExit(2)
        for leaf in _leaf_errors(exc):
            print(f"error: {type(leaf).__name__}: {leaf}", file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
