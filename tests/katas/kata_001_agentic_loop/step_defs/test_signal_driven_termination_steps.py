"""Step definitions for ``signal_driven_termination.feature`` (US1).

Why these steps exist:
    The Gherkin feature file is hash-locked by ``/iikit-04-testify`` — these
    step definitions are the only thing that may change. Each step wires
    a phrase from the feature to a real call against the loop module and
    asserts on the resulting :class:`EventRecord`s. Assertions are made
    against structured fields only (Principle I) — no step inspects the
    model's text.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession

FEATURES_DIR = Path(__file__).resolve().parents[1] / "features"

scenarios(str(FEATURES_DIR / "signal_driven_termination.feature"))


# ── Shared mutable state for one scenario ───────────────────────────────────


@dataclass
class _ScenarioState:
    session: RuntimeSession | None = None
    cause: str | None = None
    fixture_turns: list[dict] | None = None
    log_records: list[dict] = field(default_factory=list)


@pytest.fixture
def state() -> _ScenarioState:
    """Per-scenario scratchpad."""
    return _ScenarioState()


def _weather_def() -> tuple[ToolDefinition, callable]:
    definition = ToolDefinition(
        name="get_weather",
        description="Stub weather tool used by US1 fixtures.",
        input_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    )
    return definition, lambda payload: {"city": payload["city"], "temp_c": 18}


def _make_session(turns: list[dict], runs_dir: Path) -> RuntimeSession:
    sid = str(uuid.uuid4())
    definition, impl = _weather_def()
    return RuntimeSession.open(
        session_id=sid,
        model="claude-test",
        client=RecordedClient(turns),
        runs_root=runs_dir,
        tool_definitions=[(definition, impl)],
    )


def _read_log(session: RuntimeSession) -> list[dict]:
    return [
        json.loads(line)
        for line in session.event_log.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ── Background ──────────────────────────────────────────────────────────────


@given("an initialized agent session with at least one registered tool")
def _given_session(state: _ScenarioState, runs_dir: Path) -> None:
    # Default to the happy_path fixture; specific scenarios override before
    # ``run`` is called.
    state.fixture_turns = [
        {
            "id": "msg_1",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "ok"}],
        }
    ]
    state.session = _make_session(state.fixture_turns, runs_dir)


# ── Whens ───────────────────────────────────────────────────────────────────


@when(parsers.parse('the session completes a turn whose structured stop signal is "{signal}"'))
def _when_signal(state: _ScenarioState, runs_dir: Path, signal: str) -> None:
    turns = [{"id": "msg_1", "stop_reason": signal, "content": [{"type": "text", "text": "."}]}]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "drive scenario")
    state.log_records = _read_log(state.session)


@when(parsers.parse('the session returns "stop_reason={signal}" for the current turn'))
def _when_stop_reason_lit(state: _ScenarioState, runs_dir: Path, signal: str) -> None:
    if signal == "tool_use":
        turns = [
            {
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
            },
            {
                "id": "msg_2",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "ok"}],
            },
        ]
    else:
        turns = [{"id": "msg_1", "stop_reason": signal, "content": [{"type": "text", "text": "."}]}]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "drive")
    state.log_records = _read_log(state.session)


@when(
    parsers.parse(
        'the session runs a multi-turn interaction alternating "tool_use" and "end_turn" signals'
    )
)
def _when_multi_turn(state: _ScenarioState, runs_dir: Path) -> None:
    turns = [
        {
            "id": "msg_1",
            "stop_reason": "tool_use",
            "content": [
                {"type": "tool_use", "id": "tu_1", "name": "get_weather", "input": {"city": "A"}}
            ],
        },
        {
            "id": "msg_2",
            "stop_reason": "tool_use",
            "content": [
                {"type": "tool_use", "id": "tu_2", "name": "get_weather", "input": {"city": "B"}}
            ],
        },
        {
            "id": "msg_3",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "ok"}],
        },
    ]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "drive")
    state.log_records = _read_log(state.session)


@when("the session returns a response with no stop signal field")
def _when_absent(state: _ScenarioState, runs_dir: Path) -> None:
    turns = [{"id": "msg_1", "stop_reason": None, "content": [{"type": "text", "text": "?"}]}]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "drive")
    state.log_records = _read_log(state.session)


@when("the session returns a stop signal value the loop does not explicitly handle")
def _when_unknown(state: _ScenarioState, runs_dir: Path) -> None:
    turns = [
        {
            "id": "msg_1",
            "stop_reason": "cosmic_ray",
            "content": [{"type": "text", "text": "?"}],
        }
    ]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "drive")
    state.log_records = _read_log(state.session)


# ── Thens ───────────────────────────────────────────────────────────────────


@then("the loop halts and returns the final response")
def _then_halts(state: _ScenarioState) -> None:
    assert state.cause == "end_turn"
    assert state.log_records[-1]["branch_taken"] == "terminate"


@then(parsers.parse('the event log records "stop_reason={signal}" as the sole termination cause'))
def _then_event_log_terminal(state: _ScenarioState, signal: str) -> None:
    terminal = [r for r in state.log_records if r.get("termination_cause")]
    assert len(terminal) == 1
    assert terminal[0]["termination_cause"] == signal


@then("the designated tool is invoked programmatically")
def _then_tool_invoked(state: _ScenarioState) -> None:
    dispatched = [r for r in state.log_records if r["branch_taken"] == "tool_dispatch"]
    assert len(dispatched) >= 1
    assert dispatched[0]["tool_name"] == "get_weather"
    assert dispatched[0]["tool_outcome"] == "ok"


@then("the tool result is appended to conversation history")
def _then_history_has_tool_result(state: _ScenarioState) -> None:
    hist = state.session.history
    has_tool_result = any(
        any(b.get("type") == "tool_result" for b in turn.get("content", []))
        for turn in hist
        if isinstance(turn.get("content"), list)
    )
    assert has_tool_result, "expected a tool_result block appended to history"


@then("a new iteration begins without any termination decision")
def _then_continues(state: _ScenarioState) -> None:
    # The dispatch record itself MUST NOT carry a termination_cause.
    dispatched = [r for r in state.log_records if r["branch_taken"] == "tool_dispatch"]
    assert dispatched, "expected at least one tool_dispatch record"
    assert dispatched[0].get("termination_cause") is None


@then("the sequence of structured stop signals in the event log fully explains the loop trajectory")
def _then_signal_sequence_covers(state: _ScenarioState) -> None:
    # We expect exactly one record per iteration, in order, ending in a
    # terminal one — Principle VII guarantees the trajectory is on disk.
    signals = [r["stop_signal"] for r in state.log_records]
    assert signals[-1] == "end_turn"
    assert all(s in {"tool_use", "end_turn"} for s in signals)


@then("no event log entry references response text content")
def _then_no_text(state: _ScenarioState) -> None:
    for record in state.log_records:
        assert "prose_excerpt" not in record
        assert "completion_hint" not in record


@then("the loop halts within one iteration")
def _then_halts_one_iter(state: _ScenarioState) -> None:
    assert len(state.log_records) == 1


@then(parsers.parse('the event log records a termination reason tying the halt to "{label}"'))
def _then_label(state: _ScenarioState, label: str) -> None:
    assert state.log_records[-1]["termination_cause"] == label


@then("the loop halts with a protocol-violation termination reason")
def _then_protocol_halt(state: _ScenarioState) -> None:
    assert state.cause == "absent_signal"
    assert state.log_records[-1]["branch_taken"] == "halt_unhandled"


@then("no text-pattern fallback is attempted")
def _then_no_text_fallback(state: _ScenarioState) -> None:
    # Single record means we did not iterate again to attempt anything else.
    assert len(state.log_records) == 1


@then('the event log labels the termination as "unhandled stop signal"')
def _then_unhandled_label(state: _ScenarioState) -> None:
    assert state.log_records[-1]["termination_cause"] == "unhandled_signal"
