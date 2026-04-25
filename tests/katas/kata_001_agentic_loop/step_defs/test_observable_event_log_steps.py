"""Step defs for observable_event_log.feature (US3, P3).

Why each scenario re-runs the kata twice or validates against the JSON
schema directly: SC-007 (reproducibility) and SC-008 (reconstruction) are
about the log on disk, not the in-memory state. The steps therefore read
the file the writer just produced and treat it as the ground truth.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate
from pytest_bdd import given, scenarios, then, when

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.replay import reconstruct_trajectory
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry

FEATURE_FILE = Path(__file__).resolve().parents[1] / "features" / "observable_event_log.feature"
FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures"
SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "001-agentic-loop"
    / "contracts"
    / "event-log-record.schema.json"
)

scenarios(str(FEATURE_FILE))


def _registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(
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
    return reg


def _session(tmp_path):
    reg = _registry()
    return RuntimeSession(
        model="claude-test",
        tool_definitions=reg.definitions,
        registry=reg,
        runs_root=tmp_path,
    )


@pytest.fixture
def state(tmp_path):
    return {
        "tmp_path": tmp_path,
        "session": None,
        "second_session": None,
        "log_path": None,
        "second_log_path": None,
    }


@given("a completed kata run")
def given_completed_run(state):
    session = _session(state["tmp_path"] / "run_a")
    client = RecordedClient(FIXTURES_DIR / "happy_path.json")
    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    state["session"] = session
    state["log_path"] = session.event_log.path


@given("two independent runs of the kata against the same recorded session fixture")
def given_two_runs(state):
    given_completed_run(state)
    session = _session(state["tmp_path"] / "run_b")
    client = RecordedClient(FIXTURES_DIR / "happy_path.json")
    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    state["second_session"] = session
    state["second_log_path"] = session.event_log.path


@given("a completed event log")
def given_completed_log(state):
    given_completed_run(state)


@given("an event-log JSONL file produced by a run")
def given_event_log_file(state):
    given_completed_run(state)


@when("the event log is inspected")
def when_inspect(state):
    state["records"] = [
        json.loads(line) for line in state["log_path"].read_text().splitlines() if line
    ]


@when("their event logs are compared")
def when_compare(state):
    state["summary_a"] = reconstruct_trajectory(state["log_path"])
    state["summary_b"] = reconstruct_trajectory(state["second_log_path"])


@when("a reviewer reconstructs the loop's behavior from the log")
def when_reconstruct(state):
    state["summary"] = reconstruct_trajectory(state["log_path"])


@when("each record is validated against contracts/event-log-record.schema.json")
def when_validate_schema(state):
    schema = json.loads(SCHEMA_PATH.read_text())
    state["records"] = [
        json.loads(line) for line in state["log_path"].read_text().splitlines() if line
    ]
    for r in state["records"]:
        validate(instance=r, schema=schema)


@then(
    "each iteration has an entry recording iteration index, "
    "structured stop signal, branch taken, and tool name when applicable"
)
def then_records_complete(state):
    for r in state["records"]:
        assert "iteration" in r
        assert "stop_signal" in r
        assert "branch_taken" in r
        if r["branch_taken"] == "tool_dispatch":
            assert r["tool_name"] is not None


@then("the terminal iteration entry records the termination cause")
def then_terminal_cause(state):
    terminal = [r for r in state["records"] if r["termination_cause"] is not None]
    assert len(terminal) == 1


@then("the sequence of stop signals is identical across both runs")
def then_signals_identical(state):
    assert state["summary_a"].stop_signals == state["summary_b"].stop_signals


@then("the sequence of branch decisions is identical across both runs")
def then_branches_identical(state):
    assert state["summary_a"].branches == state["summary_b"].branches


@then("the termination cause is identified without consulting model text")
def then_termination_identified(state):
    assert state["summary"].termination_cause is not None


@then("the number of tool invocations is identified without consulting model text")
def then_tool_count(state):
    assert state["summary"].tool_invocations >= 0


@then("the iteration count is identified without consulting model text")
def then_iter_count(state):
    assert state["summary"].iterations >= 1


@then("every record passes schema validation")
def then_records_pass_schema(state):
    # The when step would have raised on failure; this is a safety reassertion.
    assert len(state["records"]) >= 1


@then("every record carries iteration_index, stop_signal, branch_taken fields")
def then_records_carry_fields(state):
    for r in state["records"]:
        assert "iteration" in r
        assert "stop_signal" in r
        assert "branch_taken" in r
