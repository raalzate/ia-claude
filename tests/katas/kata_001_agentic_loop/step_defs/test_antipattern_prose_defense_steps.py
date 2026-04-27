"""Step definitions for ``antipattern_prose_defense.feature`` (US2)."""

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

scenarios(str(FEATURES_DIR / "antipattern_prose_defense.feature"))


@dataclass
class _State:
    decoy: str | None = None
    signal: str | None = None
    session: RuntimeSession | None = None
    cause: str | None = None
    log: list[dict] = field(default_factory=list)
    raise_on_tool: bool = False
    malformed: bool = False


@pytest.fixture
def state() -> _State:
    return _State()


def _weather_def() -> tuple[ToolDefinition, callable]:
    definition = ToolDefinition(
        name="get_weather",
        description="Stub used by US2 fixtures.",
        input_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    )
    return definition, lambda payload: {"city": payload["city"], "temp_c": 18}


def _make_session(
    turns: list[dict],
    runs_dir: Path,
    *,
    raise_on_tool: bool = False,
) -> RuntimeSession:
    sid = str(uuid.uuid4())
    definition = ToolDefinition(
        name="get_weather",
        description="Stub used by US2 fixtures.",
        input_schema={
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    )
    if raise_on_tool:

        def impl(_payload: dict):
            raise RuntimeError("tool blew up")
    else:

        def impl(payload: dict):
            return {"city": payload["city"], "temp_c": 18}

    return RuntimeSession.open(
        session_id=sid,
        model="claude-test",
        client=RecordedClient(turns),
        runs_root=runs_dir,
        tool_definitions=[(definition, impl)],
    )


def _read(session: RuntimeSession) -> list[dict]:
    return [
        json.loads(line)
        for line in session.event_log.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ── Scenario: decoy with tool_use ──────────────────────────────────────────


@given(parsers.parse('a fixture response whose text body contains "{decoy}"'))
def _given_decoy(state: _State, decoy: str) -> None:
    state.decoy = decoy


@given(parsers.parse('the structured stop signal of that response is "{signal}"'))
def _given_signal(state: _State, signal: str) -> None:
    state.signal = signal


@when("the loop processes the response")
def _when_loop_runs(state: _State, runs_dir: Path) -> None:
    if state.malformed:
        # Malformed scenario: the Given step already declared a bad tool_use
        # block; build a fixture that names an unregistered tool so the
        # registry rejects it (FR-008) instead of dispatching it.
        turns = [
            {
                "id": "msg_mf_1",
                "stop_reason": "tool_use",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "tu_mf_1",
                        "name": "totally_unknown_tool",
                        "input": {"city": "Bogota"},
                    }
                ],
            }
        ]
    else:
        turns = [
            {
                "id": "msg_dec_1",
                "stop_reason": state.signal,
                "content": [
                    {"type": "text", "text": state.decoy or ""},
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
                "content": [{"type": "text", "text": "."}],
            },
        ]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "drive")
    state.log = _read(state.session)


@then("the tool-use branch executes")
def _then_tool_branch(state: _State) -> None:
    assert state.log[0]["branch_taken"] == "tool_dispatch"


@then("the loop continues rather than terminating")
def _then_continues_no_term(state: _State) -> None:
    # The dispatch record itself does not carry a termination cause.
    assert state.log[0].get("termination_cause") is None
    assert state.cause == "end_turn"


@then("the loop continues iterating")
def _then_continues_iterating(state: _State) -> None:
    assert any(r["branch_taken"] == "tool_dispatch" for r in state.log)


@then("the event log shows zero early exits attributable to text matching")
def _then_no_text_exit(state: _State) -> None:
    # Only a single termination record, and it is *end_turn* (signal-driven),
    # not anything that would suggest text triggered the halt.
    terminal = [r for r in state.log if r.get("termination_cause")]
    assert len(terminal) == 1
    assert terminal[0]["termination_cause"] == "end_turn"


# ── Scenario: termination decision references only structured metadata ─────


@given("any loop iteration has completed")
def _given_iter_completed(state: _State, runs_dir: Path) -> None:
    turns = [
        {
            "id": "msg_x",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "."}],
        }
    ]
    state.session = _make_session(turns, runs_dir)
    state.cause = run(state.session, "x")
    state.log = _read(state.session)


@when("the termination decision record is inspected")
def _when_inspect_term(state: _State) -> None:
    pass


@then("it references only structured stop metadata")
def _then_only_structured(state: _State) -> None:
    record = state.log[-1]
    assert record["stop_signal"] in {
        "tool_use",
        "end_turn",
        "max_tokens",
        "stop_sequence",
        "unhandled_signal",
        "absent_signal",
    }


@then("it contains no field derived from regex or substring operation on response text")
def _then_no_text_field(state: _State) -> None:
    record = state.log[-1]
    forbidden = {"prose_excerpt", "completion_hint", "phrase_match", "regex_match"}
    assert not (set(record.keys()) & forbidden)


# ── Scenario: tool error captured and loop continues ───────────────────────


@given('the current turn has "stop_reason=tool_use"')
def _given_tool_use(state: _State) -> None:
    state.signal = "tool_use"


@when("the tool invocation raises or returns a structured error")
def _when_tool_raises(state: _State, runs_dir: Path) -> None:
    turns = [
        {
            "id": "msg_te_1",
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "id": "tu_te_1",
                    "name": "get_weather",
                    "input": {"city": "Bogota"},
                }
            ],
        },
        {
            "id": "msg_te_2",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "."}],
        },
    ]
    state.session = _make_session(turns, runs_dir, raise_on_tool=True)
    state.cause = run(state.session, "x")
    state.log = _read(state.session)


@then("the failure is recorded as a structured tool-result entry in conversation history")
def _then_history_has_error(state: _State) -> None:
    found = False
    for turn in state.session.history:
        content = turn.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if block.get("type") == "tool_result" and block.get("is_error") is True:
                found = True
    assert found, "expected an is_error=True tool_result in history"


@then("the event log records the failure")
def _then_log_records_error(state: _State) -> None:
    assert state.log[0]["tool_outcome"] == "error"


@then("the loop continues under signal-driven rules without text inspection")
def _then_loop_continues_no_text(state: _State) -> None:
    # Continued past the failing tool call, terminated on the genuine end_turn.
    assert state.cause == "end_turn"
    assert state.log[-1]["termination_cause"] == "end_turn"


# ── Scenario: malformed tool_use halts ─────────────────────────────────────


@given(parsers.parse('a response carries "stop_reason=tool_use"'))
def _given_response_tool_use(state: _State) -> None:
    state.signal = "tool_use"


@given("the tool_use block is missing required fields or references an unknown tool")
def _given_malformed(state: _State) -> None:
    state.malformed = True


@then(parsers.parse('the loop halts with an "unhandled tool-use" termination reason'))
def _then_halt_malformed(state: _State) -> None:
    assert state.cause == "malformed_tool_use"
    assert state.log[-1]["termination_cause"] == "malformed_tool_use"
    assert state.log[-1]["branch_taken"] == "halt_unhandled"


@then("no heuristic recovery or text-based fallback is attempted")
def _then_no_fallback(state: _State) -> None:
    # Single record means we did not iterate again to attempt anything.
    assert len(state.log) == 1
