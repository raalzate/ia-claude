"""Prove SC-008: a reviewer rebuilds the trajectory from the log alone."""

from __future__ import annotations

from pathlib import Path

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.replay import reconstruct_trajectory
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _build_session(tmp_path):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_weather",
            description="weather",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        ),
        handler=lambda payload: {"temp_c": 18, "city": payload["city"]},
    )
    return RuntimeSession(
        model="claude-test",
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=tmp_path,
    )


def test_happy_path_trajectory_matches_live_run(tmp_path):
    session = _build_session(tmp_path)
    client = RecordedClient(FIXTURES / "happy_path.json")
    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)

    summary = reconstruct_trajectory(session.event_log.path)
    assert summary.iterations == 2
    assert summary.tool_invocations == 1
    assert summary.termination_cause == "end_turn"
    assert summary.stop_signals == ("tool_use", "end_turn")
    assert summary.branches == ("tool_dispatch", "terminate")


def test_two_runs_have_byte_identical_signal_branch_columns(tmp_path):
    """SC-007 — reproducibility from a fixed fixture."""

    def _run(label: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
        session = _build_session(tmp_path / label)
        client = RecordedClient(FIXTURES / "happy_path.json")
        result = run(session=session, client=client, initial_user_message="hi")
        session.close(termination=result)
        summary = reconstruct_trajectory(session.event_log.path)
        return summary.stop_signals, summary.branches

    a = _run("run_a")
    b = _run("run_b")
    assert a == b
