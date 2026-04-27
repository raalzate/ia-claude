"""Decoy completion phrase coverage (US2 unit guard).

Why this test is important:
    SC-004 enumerates the four phrases ("task complete", "we are done",
    "finished", "all done") that historically cause naive loops to exit
    early. This test feeds each phrase through the loop with a
    *non-terminal* structured signal and asserts the loop continues. It
    fails closed if anyone re-introduces prose-matching into ``loop.py``.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession

DECOYS = ["task complete", "we are done", "finished", "all done"]


def _build_session(turns: list[dict], runs_root: Path) -> RuntimeSession:
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
    impl = lambda payload: {"city": payload["city"], "temp_c": 18}  # noqa: E731
    return RuntimeSession.open(
        session_id=str(uuid.uuid4()),
        model="claude-test",
        client=RecordedClient(turns),
        runs_root=runs_root,
        tool_definitions=[(definition, impl)],
    )


@pytest.mark.parametrize("decoy", DECOYS)
def test_decoy_phrase_with_tool_use_does_not_terminate(
    decoy: str, runs_dir: Path, session_id: str
) -> None:
    turns = [
        {
            "id": "msg_dec_1",
            "stop_reason": "tool_use",
            "content": [
                {"type": "text", "text": decoy},
                {
                    "type": "tool_use",
                    "id": "tu_dec_1",
                    "name": "get_weather",
                    "input": {"city": "Bogota"},
                },
            ],
        },
        {
            "id": "msg_dec_2",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "real result"}],
        },
    ]
    session = _build_session(turns, runs_dir)
    cause = run(session, "trigger decoy")
    session.close()
    log = [
        json.loads(line)
        for line in session.event_log.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert cause == "end_turn"
    assert log[0]["branch_taken"] == "tool_dispatch"
    assert log[1]["termination_cause"] == "end_turn"


def test_decoy_phrase_in_absent_signal_still_halts(runs_dir: Path) -> None:
    """An absent signal halts even if prose says 'task complete'.

    Why: the halt cause must be ``absent_signal`` — driven by the missing
    structured field — *not* coincidentally by the prose content.
    """
    turns = [
        {
            "id": "msg_abs_1",
            "stop_reason": None,
            "content": [{"type": "text", "text": "task complete"}],
        }
    ]
    session = _build_session(turns, runs_dir)
    cause = run(session, "x")
    session.close()
    assert cause == "absent_signal"
