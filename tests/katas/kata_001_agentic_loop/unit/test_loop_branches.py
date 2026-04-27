"""Unit coverage for every branch of ``loop.run`` switch.

Why unit tests in addition to BDD: BDD scenarios prove the *external*
behaviour; these tests prove every internal branch is reachable and emits
the right ``EventRecord``. Together they guarantee no branch dies silently.
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import classify_stop_signal, run
from katas.kata_001_agentic_loop.models import (
    ToolDefinition,
    UnhandledStopSignal,
)
from katas.kata_001_agentic_loop.session import RuntimeSession


def _weather_tool() -> tuple[ToolDefinition, callable]:
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


def _build_session(turns: list[dict], runs_root: Path, sid: str) -> RuntimeSession:
    definition, impl = _weather_tool()
    return RuntimeSession.open(
        session_id=sid,
        model="claude-test",
        client=RecordedClient(turns),
        runs_root=runs_root,
        tool_definitions=[(definition, impl)],
    )


def _read_log(session: RuntimeSession) -> list[dict]:
    return [
        json.loads(line)
        for line in session.event_log.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ── classify_stop_signal ────────────────────────────────────────────────────


def test_classify_recognised_signals_pass_through() -> None:
    for raw in ("tool_use", "end_turn", "max_tokens", "stop_sequence"):
        assert classify_stop_signal(raw) == raw


def test_classify_unknown_signal_returns_unhandled() -> None:
    classified = classify_stop_signal("cosmic_ray")
    assert isinstance(classified, UnhandledStopSignal)
    assert classified.raw_value == "cosmic_ray"
    assert classified.reason_label == "unhandled_signal"


def test_classify_absent_signal_returns_absent_label() -> None:
    classified = classify_stop_signal(None)
    assert isinstance(classified, UnhandledStopSignal)
    assert classified.raw_value is None
    assert classified.reason_label == "absent_signal"


# ── End-to-end branches ─────────────────────────────────────────────────────


def _text_turn(stop_reason: str | None, text: str = ".") -> dict:
    return {
        "id": "msg_1",
        "stop_reason": stop_reason,
        "content": [{"type": "text", "text": text}],
    }


def _tool_use_turn() -> dict:
    return {
        "id": "msg_1",
        "stop_reason": "tool_use",
        "content": [
            {
                "type": "tool_use",
                "id": "tu_1",
                "name": "get_weather",
                "input": {"city": "Bogota"},
            }
        ],
    }


def test_branch_end_turn_terminates_cleanly(runs_dir: Path, session_id: str) -> None:
    session = _build_session([_text_turn("end_turn", "ok")], runs_dir, session_id)
    cause = run(session, "hello")
    session.close()
    assert cause == "end_turn"
    log = _read_log(session)
    assert len(log) == 1
    assert log[0]["termination_cause"] == "end_turn"
    assert log[0]["branch_taken"] == "terminate"


def test_branch_tool_use_dispatches_then_terminates(runs_dir: Path, session_id: str) -> None:
    turns = [_tool_use_turn(), _text_turn("end_turn", "done")]
    session = _build_session(turns, runs_dir, session_id)
    cause = run(session, "weather please")
    session.close()
    assert cause == "end_turn"
    log = _read_log(session)
    assert len(log) == 2
    assert log[0]["branch_taken"] == "tool_dispatch"
    assert log[0]["tool_name"] == "get_weather"
    assert log[0]["tool_outcome"] == "ok"
    assert log[1]["termination_cause"] == "end_turn"


def test_branch_max_tokens_halts_with_label(runs_dir: Path, session_id: str) -> None:
    session = _build_session([_text_turn("max_tokens", "trun")], runs_dir, session_id)
    cause = run(session, "explain")
    session.close()
    assert cause == "max_tokens"
    log = _read_log(session)
    assert log[-1]["termination_cause"] == "max_tokens"


def test_branch_stop_sequence_halts_with_label(runs_dir: Path, session_id: str) -> None:
    turns = [{"id": "msg_1", "stop_reason": "stop_sequence", "content": []}]
    session = _build_session(turns, runs_dir, session_id)
    cause = run(session, "x")
    session.close()
    assert cause == "stop_sequence"
    log = _read_log(session)
    assert log[-1]["termination_cause"] == "stop_sequence"


def test_branch_unknown_signal_halts_unhandled(runs_dir: Path, session_id: str) -> None:
    session = _build_session([_text_turn("cosmic_ray", "?")], runs_dir, session_id)
    cause = run(session, "x")
    session.close()
    assert cause == "unhandled_signal"
    log = _read_log(session)
    assert log[-1]["branch_taken"] == "halt_unhandled"


def test_branch_absent_signal_halts_with_protocol_label(runs_dir: Path, session_id: str) -> None:
    session = _build_session([_text_turn(None, "task complete")], runs_dir, session_id)
    cause = run(session, "x")
    session.close()
    assert cause == "absent_signal"
    log = _read_log(session)
    assert log[-1]["termination_cause"] == "absent_signal"


def test_event_log_carries_no_text_field(runs_dir: Path, session_id: str) -> None:
    """Every record must conform to EventRecord — no prose fields permitted."""
    session = _build_session([_text_turn("end_turn", "we are done")], runs_dir, session_id)
    run(session, "x")
    session.close()
    for record in _read_log(session):
        assert "prose_excerpt" not in record
        assert "completion_hint" not in record
        assert set(record.keys()) <= {
            "session_id",
            "iteration",
            "timestamp",
            "stop_signal",
            "branch_taken",
            "tool_name",
            "tool_outcome",
            "termination_cause",
        }
