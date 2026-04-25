"""Step defs for antipattern_prose_defense.feature (US2, P2).

Why these steps look almost identical to the US1 ones: the kata's whole
point is that "decoy text in prose" is structurally indistinguishable from
any other prose to the loop. The step-def code therefore makes no special
case for the decoy fixture — it only swaps which fixture the RecordedClient
loads and asserts the same event-log invariants hold.
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
    Path(__file__).resolve().parents[1]
    / "features"
    / "antipattern_prose_defense.feature"
)
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"

scenarios(str(FEATURE_FILE))


@pytest.fixture
def registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
        ToolDefinition(
            name="get_weather",
            description="Look up weather.",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        ),
        handler=lambda payload: {"temp_c": 18, "city": payload["city"]},
    )
    # Why we register a handler that raises: the tool_error fixture invokes
    # `explode`. FR-007 says the loop wraps the failure as a structured
    # ToolResult and keeps going.
    def _explode(_input):
        raise RuntimeError("synthetic failure for FR-007")

    reg.register(
        ToolDefinition(
            name="explode",
            description="Always fails.",
            input_schema={"type": "object", "additionalProperties": True},
        ),
        handler=_explode,
    )
    return reg


@pytest.fixture
def state(tmp_path, registry):
    return {
        "tmp_path": tmp_path,
        "registry": registry,
        "session": RuntimeSession(
            model="claude-test",
            tool_definitions=registry.definitions,
            registry=registry,
            runs_root=tmp_path,
        ),
        "fixture_name": None,
        "result": None,
    }


def _records(state) -> list[dict]:
    return [
        json.loads(line)
        for line in state["session"].event_log.path.read_text().splitlines()
        if line
    ]


# --------------------------------------------------------------------------- #
# Given                                                                       #
# --------------------------------------------------------------------------- #


@given(parsers.parse('a fixture response whose text body contains "{decoy}"'))
def given_decoy(state, decoy):
    # Why we do not switch fixtures here: every decoy phrase listed in the
    # Examples table appears in decoy_phrase.json's first turn text. Loading
    # that fixture once covers the whole table.
    state["fixture_name"] = "decoy_phrase"


@given(parsers.parse('the structured stop signal of that response is "{signal}"'))
def given_signal(state, signal):
    state["expected_signal"] = signal


@given('the current turn has "stop_reason=tool_use"')
def given_current_tool_use(state):
    state["fixture_name"] = "tool_error"


@given('a response carries "stop_reason=tool_use"')
def given_response_tool_use(state):
    state["fixture_name"] = "malformed_tool_use"


@given("the tool_use block is missing required fields or references an unknown tool")
def given_unknown_tool(state):
    # Already true by virtue of fixture choice; no-op.
    assert state["fixture_name"] == "malformed_tool_use"


@given("any loop iteration has completed")
def given_iteration_completed(state):
    state["fixture_name"] = "decoy_phrase"


# --------------------------------------------------------------------------- #
# When                                                                        #
# --------------------------------------------------------------------------- #


def _drive(state) -> None:
    client = RecordedClient(FIXTURES_DIR / f"{state['fixture_name']}.json")
    state["result"] = run(
        session=state["session"], client=client, initial_user_message="hi"
    )
    state["session"].close(termination=state["result"])


@when("the loop processes the response")
def when_processes(state):
    _drive(state)


@when("the tool invocation raises or returns a structured error")
def when_tool_raises(state):
    _drive(state)


@when("the termination decision record is inspected")
def when_inspect(state):
    _drive(state)


# --------------------------------------------------------------------------- #
# Then                                                                        #
# --------------------------------------------------------------------------- #


@then("the tool-use branch executes")
def then_tool_use_branch(state):
    records = _records(state)
    assert any(r["branch_taken"] == "tool_dispatch" for r in records)


@then("the loop continues rather than terminating")
def then_loop_continues(state):
    # The decoy fixture ends with end_turn, so result is "end_turn" — but
    # critically the FIRST iteration must NOT terminate.
    records = _records(state)
    assert records[0]["branch_taken"] == "tool_dispatch"
    assert records[0]["termination_cause"] is None


@then("the loop continues iterating")
def then_loop_continues_iter(state):
    records = _records(state)
    assert records[0]["branch_taken"] == "tool_dispatch"


@then("the event log shows zero early exits attributable to text matching")
def then_zero_early_exits(state):
    records = _records(state)
    early_exits = [
        r for r in records[:-1]
        if r.get("termination_cause") is not None
    ]
    assert early_exits == []


@then("it references only structured stop metadata")
def then_only_structured(state):
    records = _records(state)
    valid_signals = {
        "tool_use",
        "end_turn",
        "max_tokens",
        "stop_sequence",
        "unhandled_signal",
        "absent_signal",
    }
    for r in records:
        assert r["stop_signal"] in valid_signals


@then("it contains no field derived from regex or substring operation on response text")
def then_no_text_field(state):
    records = _records(state)
    forbidden_keys = {
        "matched_phrase",
        "regex_match",
        "prose_excerpt",
        "completion_hint",
        "text",
    }
    for r in records:
        assert forbidden_keys.isdisjoint(r.keys())


@then("the failure is recorded as a structured tool-result entry in conversation history")
def then_structured_failure(state):
    history = state["session"].history
    found_error = False
    for entry in history:
        content = entry.get("content")
        if isinstance(content, list):
            for block in content:
                if (
                    block.get("type") == "tool_result"
                    and block.get("is_error") is True
                ):
                    found_error = True
    assert found_error, "expected a tool_result block with is_error=True"


@then("the event log records the failure")
def then_event_records_failure(state):
    records = _records(state)
    assert any(
        r["branch_taken"] == "tool_dispatch" and r["tool_outcome"] == "error"
        for r in records
    )


@then("the loop continues under signal-driven rules without text inspection")
def then_continues_signal_driven(state):
    records = _records(state)
    # Loop kept going past the failing tool dispatch.
    assert records[-1]["termination_cause"] == "end_turn"


@then('the loop halts with an "unhandled tool-use" termination reason')
def then_halts_unhandled_tool(state):
    records = _records(state)
    assert records[-1]["termination_cause"] == "malformed_tool_use"


@then("no heuristic recovery or text-based fallback is attempted")
def then_no_heuristic(state):
    records = _records(state)
    # No tool_dispatch record before the malformed halt — we did not partial-
    # dispatch on a guess.
    pre_halt = records[:-1]
    assert all(r["branch_taken"] != "tool_dispatch" for r in pre_halt)
