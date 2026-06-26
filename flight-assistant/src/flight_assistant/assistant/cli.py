"""Command-line entry point for the flight route-discovery assistant.

Usage:
    flight-assistant "Can I fly from Berlin to Lisbon directly?"
    flight-assistant            # interactive REPL
    flight-assistant --demo     # run a scripted set of demo queries

The CLI spawns the MCP server as a subprocess via the agent's MCP client and
uses an LLM (OpenAI function-calling) to orchestrate the tools. Set
``OPENAI_API_KEY`` (or ``OPENAI_BASE_URL`` for a local OpenAI-compatible server)
to run it. The MCP server, tests, and MCP hosts work without a key.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from .agent import Agent, MissingCredentialsError

DEMO_QUERIES = [
    "Can I fly from Berlin to Lisbon directly?",
    "Find airports in Portugal",
    "What is airport BER?",
    "from Tokyo to Reykjavik",  # likely no direct route -> alternatives
    "alternatives from Berlin to New York",
]


async def _run_once(agent: Agent, query: str) -> None:
    print(f"\n\033[1m▶ {query}\033[0m")
    answer = await agent.answer(query)
    print(answer)


async def _repl(agent: Agent) -> None:
    print("Flight route-discovery assistant. Type a question, or 'quit' to exit.\n")
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
        print(await agent.answer(query))
        print()


async def _demo(agent: Agent) -> None:
    print("Running demo queries")
    for q in DEMO_QUERIES:
        await _run_once(agent, q)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flight route-discovery assistant")
    parser.add_argument("query", nargs="*", help="A natural-language route question.")
    parser.add_argument("--demo", action="store_true", help="Run scripted demo queries.")
    parser.add_argument(
        "--model", help="Override the LLM model (default: OPENAI_MODEL or gpt-4o-mini)."
    )
    args = parser.parse_args()

    agent = Agent(model=args.model)

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


if __name__ == "__main__":
    main()
