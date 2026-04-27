"""CLI entrypoint for Kata 1.

Why this exists:
    The loop is callable from Python directly, but the kata's quickstart
    (``specs/001-agentic-loop/quickstart.md``) advertises a one-liner
    invocation. ``runner`` wires the loop to a :class:`LiveClient` (when
    ``LIVE_API=1``) or a :class:`RecordedClient` (default), declares one
    sample tool, and prints the path of the resulting event log so the
    practitioner can ``jq`` it immediately.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path

from .client import LiveClient, RecordedClient
from .models import ToolDefinition
from .replay import reconstruct_trajectory
from .session import RuntimeSession


def _sample_get_weather() -> tuple[ToolDefinition, callable]:
    """Declare the canonical ``get_weather`` tool used by quickstart.

    Why: every kata run needs at least one tool registered to exercise the
    ``tool_use`` branch — and a deterministic stub keeps the runner usable
    without external services.
    """
    definition = ToolDefinition(
        name="get_weather",
        description="Return a fake weather report. Used to demonstrate tool_use.",
        input_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    )

    def impl(payload: dict) -> dict:
        return {"city": payload["city"], "temp_c": 18, "conditions": "clear"}

    return definition, impl


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser exposed by ``python -m katas.kata_001_agentic_loop.runner``."""
    parser = argparse.ArgumentParser(prog="kata-001-agentic-loop")
    parser.add_argument("--model", default="claude-opus-4-7")
    parser.add_argument("--prompt", required=True, help="Initial user message")
    parser.add_argument("--fixture", default=None, help="Recorded fixture name (offline mode)")
    parser.add_argument("--runs-root", default="runs", help="Where to write runs/<id>/")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run one kata session end-to-end. Returns 0 on a clean terminal halt."""
    args = build_parser().parse_args(argv)

    runs_root = Path(args.runs_root)
    runs_root.mkdir(parents=True, exist_ok=True)
    session_id = str(uuid.uuid4())

    if os.environ.get("LIVE_API") == "1":
        client = LiveClient(model=args.model)
    elif args.fixture:
        fixture_path = (
            Path(__file__).resolve().parents[2]
            / "tests"
            / "katas"
            / "kata_001_agentic_loop"
            / "fixtures"
            / f"{args.fixture}.json"
        )
        client = RecordedClient.from_fixture(fixture_path)
    else:
        sys.stderr.write("error: provide --fixture or set LIVE_API=1\n")
        return 2

    definition, impl = _sample_get_weather()
    session = RuntimeSession.open(
        session_id=session_id,
        model=args.model,
        client=client,
        runs_root=runs_root,
        tool_definitions=[(definition, impl)],
    )
    try:
        from .loop import run as run_loop  # noqa: PLC0415 — break circular import

        cause = run_loop(session, args.prompt)
    finally:
        session.close()

    # Read the summary back from the log to prove the log is sufficient.
    summary = reconstruct_trajectory(session.event_log.path)
    print(
        json.dumps(
            {
                "session_id": session_id,
                "iterations": summary.iterations,
                "tool_invocations": summary.tool_invocations,
                "termination_cause": summary.termination_cause,
                "events_log": str(session.event_log.path),
            },
            sort_keys=True,
        )
    )
    return 0 if cause == "end_turn" else 1


if __name__ == "__main__":  # pragma: no cover — CLI entry only
    sys.exit(main())
