"""Trajectory reconstruction from the event log alone (proves SC-008).

Why: a reviewer must be able to extract iteration count, tool invocations,
and termination cause from the JSONL file *without* reading source. This
test feeds a hand-crafted log to ``replay.reconstruct_trajectory`` and
asserts the three numbers come out right — no ``katas.kata_001_agentic_loop.loop``
import involved in the assertion.
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_001_agentic_loop.replay import reconstruct_trajectory


def _record(
    iteration: int,
    *,
    branch: str,
    signal: str,
    tool_name: str | None = None,
    tool_outcome: str | None = None,
    termination_cause: str | None = None,
) -> str:
    return json.dumps(
        {
            "branch_taken": branch,
            "iteration": iteration,
            "session_id": "s",
            "stop_signal": signal,
            "termination_cause": termination_cause,
            "timestamp": f"2026-01-01T00:00:0{iteration}Z",
            "tool_name": tool_name,
            "tool_outcome": tool_outcome,
        },
        sort_keys=True,
    )


_DISPATCH = dict(branch="tool_dispatch", signal="tool_use", tool_name="get_weather")
SAMPLE_LOG = (
    "\n".join(
        [
            _record(0, **_DISPATCH, tool_outcome="ok"),
            _record(1, **_DISPATCH, tool_outcome="error"),
            _record(2, branch="terminate", signal="end_turn", termination_cause="end_turn"),
        ]
    )
    + "\n"
)


def test_reconstruct_iterations_and_tools(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log_path.write_text(SAMPLE_LOG, encoding="utf-8")
    summary = reconstruct_trajectory(log_path)
    assert summary.iterations == 3
    assert summary.tool_invocations == 2
    assert summary.termination_cause == "end_turn"


def test_reconstruct_handles_blank_lines(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log_path.write_text("\n" + SAMPLE_LOG + "\n\n", encoding="utf-8")
    summary = reconstruct_trajectory(log_path)
    assert summary.iterations == 3


def test_reconstruct_no_terminal_returns_none(tmp_path: Path) -> None:
    log_path = tmp_path / "events.jsonl"
    log_path.write_text(
        _record(0, **_DISPATCH, tool_outcome="ok") + "\n",
        encoding="utf-8",
    )
    summary = reconstruct_trajectory(log_path)
    assert summary.iterations == 1
    assert summary.tool_invocations == 1
    assert summary.termination_cause is None
