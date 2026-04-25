"""CLI entrypoint: `python -m katas.kata_001_agentic_loop.runner ...`.

Why a tiny runner: the kata's value is the LOOP, not the launcher. The
runner only wires CLI args to a session, picks live-vs-recorded by env, and
prints the path to the resulting event log so a practitioner can `jq` it
straight away (see quickstart.md).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from katas.kata_001_agentic_loop.client import LiveClient, MessagesClient, RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry


def _default_registry() -> ToolRegistry:
    """Workshop-default registry: a single `get_weather` echo tool.

    Why we ship a default: a kata practitioner typing
    `python -m katas.kata_001_agentic_loop.runner` should get a working
    end-to-end loop without first having to register a tool. Tools they
    care about belong in their own scripts.
    """
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_weather",
            description="Echo the requested city back with a fixed temperature reading.",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        ),
        handler=lambda payload: {"temp_c": 18, "city": payload["city"]},
    )
    return registry


def _build_client(args: argparse.Namespace) -> MessagesClient:
    """Pick LiveClient when LIVE_API=1, else RecordedClient on a fixture.

    Why an env var instead of a flag: it makes "use live" a deliberate
    opt-in (you can't accidentally burn API budget by typing the wrong arg).
    """
    live = os.environ.get("LIVE_API") == "1"
    if live:
        return LiveClient(api_key=os.environ.get("ANTHROPIC_API_KEY"))
    fixture = Path(args.fixture) if args.fixture else None
    if fixture is None:
        raise SystemExit(
            "no fixture supplied and LIVE_API is not set — pass --fixture <path> or set LIVE_API=1"
        )
    return RecordedClient(fixture)


def _summary_from_log(events_path: Path) -> dict:
    """Reconstruct (iterations, tool_invocations, termination_cause) from the log.

    Why we re-read the log instead of trusting in-memory counters: SC-008
    requires the log to be the single source of truth. Reading it back
    proves it is.
    """
    iterations = 0
    tool_invocations = 0
    termination_cause: str | None = None
    for line in events_path.read_text().splitlines():
        if not line:
            continue
        record = json.loads(line)
        iterations = max(iterations, record["iteration"] + 1)
        if record["branch_taken"] == "tool_dispatch":
            tool_invocations += 1
        if record["termination_cause"]:
            termination_cause = record["termination_cause"]
    return {
        "iterations": iterations,
        "tool_invocations": tool_invocations,
        "termination_cause": termination_cause,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint — drive a kata run and print a JSON summary."""
    parser = argparse.ArgumentParser(prog="kata_001_agentic_loop")
    parser.add_argument("--model", default="claude-opus-4-7")
    parser.add_argument("--prompt", default="What is the weather in Bogotá?")
    parser.add_argument(
        "--fixture",
        default=None,
        help="Path to a recorded session JSON fixture (ignored if LIVE_API=1)",
    )
    parser.add_argument("--runs-root", default="runs")
    args = parser.parse_args(argv)

    registry = _default_registry()
    session = RuntimeSession(
        model=args.model,
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=args.runs_root,
    )
    client = _build_client(args)

    cause = run(
        session=session,
        client=client,
        initial_user_message=args.prompt,
    )
    session.close(termination=cause)

    summary = _summary_from_log(session.event_log.path)
    summary["session_id"] = session.session_id
    summary["events_jsonl"] = str(session.event_log.path)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
