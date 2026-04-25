"""FR-010 — conversation history preserves the trajectory's order.

Why this is in unit (not BDD): the BDD scenarios assert on the event log; this
asserts on the in-memory history. Together they prove FR-010 — the history is
sufficient to replay the signal-driven decisions in order, which is what makes
two runs diff byte-identical (SC-007).
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.replay import reconstruct_trajectory
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_history_role_order_matches_event_branches(tmp_path):
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
    session = RuntimeSession(
        model="claude-test",
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=tmp_path,
    )
    client = RecordedClient(FIXTURES / "happy_path.json")
    run(session=session, client=client, initial_user_message="hi")
    session.close(termination="end_turn")

    summary = reconstruct_trajectory(session.event_log.path)
    # Signal/branch trajectory from the log.
    assert summary.stop_signals == ("tool_use", "end_turn")
    assert summary.branches == ("tool_dispatch", "terminate")

    # Conversation history mirrors that trajectory in order:
    # user -> assistant(tool_use) -> user(tool_result) -> assistant(end_turn)
    history = session.history
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"
    assert history[1]["stop_reason"] == "tool_use"
    assert history[2]["role"] == "user"
    assert isinstance(history[2]["content"], list)
    assert history[2]["content"][0]["type"] == "tool_result"
    assert history[3]["role"] == "assistant"
    assert history[3]["stop_reason"] == "end_turn"


def test_history_json_persisted_for_replay(tmp_path):
    """The mirror file under runs/<id>/history.json exists after close."""
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
    session = RuntimeSession(
        model="claude-test",
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=tmp_path,
    )
    client = RecordedClient(FIXTURES / "happy_path.json")
    run(session=session, client=client, initial_user_message="hi")
    session.close(termination="end_turn")

    history_path = session.event_log.path.parent / "history.json"
    assert history_path.exists()
    rehydrated = json.loads(history_path.read_text())
    assert rehydrated[0]["role"] == "user"
    assert rehydrated[-1]["role"] == "assistant"
