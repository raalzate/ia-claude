"""Step definitions for signal_driven_termination.feature (US1, P1).

Why each Then asserts on EventRecord rows (not on prose): the kata under test
is exactly "decisions are made on signals, not text". The step bindings model
that — every assertion reads `event_log` records, never `assistant_text`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry

FEATURE_FILE = (
    Path(__file__).resolve().parents[1] / "features" / "signal_driven_termination.feature"
)
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

# Bind every scenario in the feature file at import time. pytest-bdd will
# generate one test function per @TS-* scenario.
scenarios(str(FEATURE_FILE))


# --------------------------------------------------------------------------- #
# Fixture: a registry with a single registered tool, so the Background step   #
# 'session with at least one registered tool' is satisfiable.                 #
# --------------------------------------------------------------------------- #


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        ToolDefinition(
            name="get_weather",
            description="Look up weather for a city.",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        ),
        handler=lambda payload: {"temp_c": 18, "city": payload["city"]},
    )
    return reg


@pytest.fixture
def state(tmp_path, registry):
    """Cross-step state holder. Why a dict: simplest pytest-bdd pattern for
    sharing values between Given/When/Then without leaking globals."""
    return {
        "tmp_path": tmp_path,
        "registry": registry,
        "session": None,
        "result": None,
        "fixture_name": None,
    }


# --------------------------------------------------------------------------- #
# Background                                                                  #
# --------------------------------------------------------------------------- #


@given("an initialized agent session with at least one registered tool")
def init_session(state):
    state["session"] = RuntimeSession(
        model="claude-test",
        tool_definitions=state["registry"].definitions,
        registry=state["registry"],
        runs_root=state["tmp_path"],
    )


# --------------------------------------------------------------------------- #
# When clauses — pick the recorded fixture matching each scenario             #
# --------------------------------------------------------------------------- #


@when(parsers.parse('the session completes a turn whose structured stop signal is "{signal}"'))
def session_completes_with_signal(state, signal):
    fixture_map = {
        "end_turn": "happy_path",
        "max_tokens": "max_tokens",
    }
    state["fixture_name"] = fixture_map[signal]
    client = RecordedClient(FIXTURES_DIR / f"{state['fixture_name']}.json")
    state["result"] = run(session=state["session"], client=client, initial_user_message="hi")
    state["session"].close(termination=state["result"])


@when(parsers.parse('the session returns "stop_reason=tool_use" for the current turn'))
def session_returns_tool_use(state):
    # Drive against happy_path so the FIRST turn is tool_use; we don't run to
    # termination here — the assertion looks at the first record only.
    client = RecordedClient(FIXTURES_DIR / "happy_path.json")
    state["fixture_name"] = "happy_path"
    state["result"] = run(session=state["session"], client=client, initial_user_message="hi")
    state["session"].close(termination=state["result"])


@when('the session runs a multi-turn interaction alternating "tool_use" and "end_turn" signals')
def session_runs_multiturn(state):
    client = RecordedClient(FIXTURES_DIR / "happy_path.json")
    state["fixture_name"] = "happy_path"
    state["result"] = run(session=state["session"], client=client, initial_user_message="hi")
    state["session"].close(termination=state["result"])


@when("the session returns a response with no stop signal field")
def session_returns_absent(state):
    client = RecordedClient(FIXTURES_DIR / "absent_signal.json")
    state["fixture_name"] = "absent_signal"
    state["result"] = run(session=state["session"], client=client, initial_user_message="hi")
    state["session"].close(termination=state["result"])


@when("the session returns a stop signal value the loop does not explicitly handle")
def session_returns_unknown(state):
    client = RecordedClient(FIXTURES_DIR / "unknown_signal.json")
    state["fixture_name"] = "unknown_signal"
    state["result"] = run(session=state["session"], client=client, initial_user_message="hi")
    state["session"].close(termination=state["result"])


# --------------------------------------------------------------------------- #
# Then clauses                                                                #
# --------------------------------------------------------------------------- #


def _records(state) -> list[dict]:
    path = state["session"].event_log.path
    return [json.loads(line) for line in path.read_text().splitlines() if line]


@then("the loop halts and returns the final response")
def loop_halts(state):
    assert state["result"] in {
        "end_turn",
        "max_tokens",
        "stop_sequence",
        "unhandled_signal",
        "absent_signal",
        "malformed_tool_use",
    }


@then(parsers.parse('the event log records "stop_reason={signal}" as the sole termination cause'))
def event_log_termination_cause(state, signal):
    records = _records(state)
    terminal = [r for r in records if r["termination_cause"] is not None]
    assert len(terminal) == 1
    assert terminal[0]["termination_cause"] == signal


@then("the designated tool is invoked programmatically")
def tool_invoked(state):
    records = _records(state)
    assert any(
        r["branch_taken"] == "tool_dispatch" and r["tool_name"] == "get_weather" for r in records
    )


@then("the tool result is appended to conversation history")
def tool_result_appended(state):
    history = state["session"].history
    assert any(
        isinstance(entry.get("content"), list)
        and any(block.get("type") == "tool_result" for block in entry["content"])
        for entry in history
    )


@then("a new iteration begins without any termination decision")
def new_iteration_no_termination(state):
    records = _records(state)
    # The tool_dispatch record carries no termination_cause.
    dispatch_records = [r for r in records if r["branch_taken"] == "tool_dispatch"]
    assert dispatch_records, "expected at least one tool_dispatch record"
    for r in dispatch_records:
        assert r["termination_cause"] is None


@then("the sequence of structured stop signals in the event log fully explains the loop trajectory")
def trajectory_explained(state):
    records = _records(state)
    # Every record has a known stop_signal value — the loop's full path is
    # reconstructible from these alone.
    valid = {
        "tool_use",
        "end_turn",
        "max_tokens",
        "stop_sequence",
        "unhandled_signal",
        "absent_signal",
    }
    for r in records:
        assert r["stop_signal"] in valid


@then("no event log entry references response text content")
def no_text_in_log(state):
    records = _records(state)
    forbidden_keys = {"text", "prose_excerpt", "completion_hint", "assistant_text"}
    for r in records:
        assert forbidden_keys.isdisjoint(r.keys())


@then("the loop halts within one iteration")
def loop_halts_one_iteration(state):
    records = _records(state)
    assert len(records) == 1


@then(parsers.parse('the event log records a termination reason tying the halt to "{signal}"'))
def event_log_records_signal_termination(state, signal):
    records = _records(state)
    assert records[-1]["termination_cause"] == signal


@then("the loop halts with a protocol-violation termination reason")
def loop_halts_protocol_violation(state):
    records = _records(state)
    assert records[-1]["termination_cause"] == "absent_signal"
    assert records[-1]["branch_taken"] == "halt_unhandled"


@then("no text-pattern fallback is attempted")
def no_text_fallback(state):
    # The absence of any text-derived field on the EventRecord proves it.
    records = _records(state)
    forbidden_keys = {"text", "prose_excerpt", "matched_phrase"}
    for r in records:
        assert forbidden_keys.isdisjoint(r.keys())


@then('the event log labels the termination as "unhandled stop signal"')
def event_log_unhandled(state):
    records = _records(state)
    assert records[-1]["termination_cause"] == "unhandled_signal"
    assert records[-1]["branch_taken"] == "halt_unhandled"
