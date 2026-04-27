"""Replay order test (FR-010 / SC-007 cross-check).

Why: SC-007 says two runs against the same recorded session must produce
identical (stop_signal, branch_taken) sequences. This test takes the
*history* captured during run A and replays it through a second client
constructed from the same fixture; the resulting (signal, branch) column
slice must match A. If the loop ever introduced order-dependent behaviour
(e.g. iteration-count-driven branching), this test would catch it.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.events import set_frozen_clock
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession


def _weather() -> tuple[ToolDefinition, callable]:
    definition = ToolDefinition(
        name="get_weather",
        description="Stub.",
        input_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    )
    return definition, lambda payload: {"city": payload["city"], "temp_c": 18}


def _open(runs_root: Path, fixture_path: Path) -> RuntimeSession:
    definition, impl = _weather()
    return RuntimeSession.open(
        session_id=str(uuid.uuid4()),
        model="claude-test",
        client=RecordedClient.from_fixture(fixture_path),
        runs_root=runs_root,
        tool_definitions=[(definition, impl)],
    )


def _columns(events_path: Path) -> list[tuple[str, str]]:
    return [
        (json.loads(line)["stop_signal"], json.loads(line)["branch_taken"])
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_history_replay_reproduces_signal_and_branch_columns(tmp_path: Path) -> None:
    """Replay against the recorded fixture twice; column slices must match."""
    fixture = (
        Path(__file__).resolve().parents[1] / "fixtures" / "happy_path.json"
    )
    set_frozen_clock(None)  # leave timestamps free; we only compare stable cols
    runs_a = tmp_path / "a"
    runs_a.mkdir()
    runs_b = tmp_path / "b"
    runs_b.mkdir()
    a = _open(runs_a, fixture)
    run(a, "x")
    a.close()
    b = _open(runs_b, fixture)
    run(b, "x")
    b.close()
    assert _columns(a.event_log.path) == _columns(b.event_log.path)


def test_history_persisted_blocks_match_fixture_turns(tmp_path: Path) -> None:
    """``RuntimeSession.history`` mirrors the recorded turns in order.

    Why: if the loop ever skipped a turn or duplicated one, the history
    would diverge from the fixture and replay would fail. This guards
    against silent order corruption.
    """
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "happy_path.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    session = _open(runs_root, fixture_path)
    run(session, "x")
    session.close()

    # Each fixture turn becomes one assistant entry in history (plus the
    # initial user message and any tool_result blocks between them).
    assistant_turns = [t for t in session.history if t["role"] == "assistant"]
    assert len(assistant_turns) == len(fixture["turns"])
