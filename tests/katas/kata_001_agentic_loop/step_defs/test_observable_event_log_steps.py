"""Step definitions for ``observable_event_log.feature`` (US3).

Why: this user story proves the event log is sufficient for offline
reconstruction (SC-008) AND byte-deterministic across two independent runs
(SC-007). The steps run the canonical fixture twice with a frozen clock,
compare the (stop_signal, branch_taken) sequences, and validate every
record against the JSON schema.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from pytest_bdd import given, scenarios, then, when

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.events import set_frozen_clock
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.replay import reconstruct_trajectory
from katas.kata_001_agentic_loop.session import RuntimeSession

FEATURES_DIR = Path(__file__).resolve().parents[1] / "features"

scenarios(str(FEATURES_DIR / "observable_event_log.feature"))


@dataclass
class _State:
    log_a: list[dict] = field(default_factory=list)
    log_b: list[dict] = field(default_factory=list)
    log_path: Path | None = None


@pytest.fixture
def state() -> _State:
    return _State()


@pytest.fixture(autouse=True)
def _frozen_clock():
    set_frozen_clock(datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC))
    yield
    set_frozen_clock(None)


def _run_against_happy_path(runs_dir: Path) -> RuntimeSession:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "happy_path.json"
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
    session = RuntimeSession.open(
        session_id="00000000-0000-0000-0000-000000000000",
        model="claude-test",
        client=RecordedClient.from_fixture(fixture),
        runs_root=runs_dir,
        tool_definitions=[(definition, lambda payload: {"city": payload["city"], "temp_c": 18})],
    )
    run(session, "drive")
    session.close()
    return session


def _read(session_path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in session_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# ── Givens / Whens ──────────────────────────────────────────────────────────


@given("a completed kata run")
def _given_run(state: _State, runs_dir: Path) -> None:
    session = _run_against_happy_path(runs_dir)
    state.log_a = _read(session.event_log.path)
    state.log_path = session.event_log.path


@given("two independent runs of the kata against the same recorded session fixture")
def _given_two_runs(state: _State, runs_dir: Path, tmp_path: Path) -> None:
    session_a = _run_against_happy_path(runs_dir)
    session_b_root = tmp_path / "runs_b"
    session_b_root.mkdir()
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / "happy_path.json"
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
    session_b = RuntimeSession.open(
        session_id="00000000-0000-0000-0000-000000000000",
        model="claude-test",
        client=RecordedClient.from_fixture(fixture),
        runs_root=session_b_root,
        tool_definitions=[(definition, lambda payload: {"city": payload["city"], "temp_c": 18})],
    )
    run(session_b, "drive")
    session_b.close()
    state.log_a = _read(session_a.event_log.path)
    state.log_b = _read(session_b.event_log.path)


@given("a completed event log")
def _given_completed_log(state: _State, runs_dir: Path) -> None:
    session = _run_against_happy_path(runs_dir)
    state.log_a = _read(session.event_log.path)
    state.log_path = session.event_log.path


@given("an event-log JSONL file produced by a run")
def _given_jsonl(state: _State, runs_dir: Path) -> None:
    session = _run_against_happy_path(runs_dir)
    state.log_a = _read(session.event_log.path)
    state.log_path = session.event_log.path


@when("the event log is inspected")
def _when_inspect(state: _State) -> None:
    pass


@when("their event logs are compared")
def _when_compare(state: _State) -> None:
    pass


@when("a reviewer reconstructs the loop's behavior from the log")
def _when_reconstruct(state: _State) -> None:
    pass


@when("each record is validated against contracts/event-log-record.schema.json")
def _when_validate(state: _State, schema_loader) -> None:
    schema = schema_loader("event-log-record")
    validator = Draft202012Validator(schema)
    for record in state.log_a:
        validator.validate(record)


# ── Thens ───────────────────────────────────────────────────────────────────


@then(
    "each iteration has an entry recording iteration index, structured stop signal, "
    "branch taken, and tool name when applicable"
)
def _then_each_iter(state: _State) -> None:
    seen_iterations = {r["iteration"] for r in state.log_a}
    assert seen_iterations == set(range(len(state.log_a)))
    for record in state.log_a:
        assert "iteration" in record
        assert "stop_signal" in record
        assert "branch_taken" in record
        if record["branch_taken"] == "tool_dispatch":
            assert record.get("tool_name") is not None


@then("the terminal iteration entry records the termination cause")
def _then_terminal_record(state: _State) -> None:
    assert state.log_a[-1].get("termination_cause") is not None


@then("the sequence of stop signals is identical across both runs")
def _then_signals_identical(state: _State) -> None:
    assert [r["stop_signal"] for r in state.log_a] == [r["stop_signal"] for r in state.log_b]


@then("the sequence of branch decisions is identical across both runs")
def _then_branches_identical(state: _State) -> None:
    assert [r["branch_taken"] for r in state.log_a] == [r["branch_taken"] for r in state.log_b]


@then("the termination cause is identified without consulting model text")
def _then_termcause(state: _State) -> None:
    summary = reconstruct_trajectory(state.log_path)
    assert summary.termination_cause == "end_turn"


@then("the number of tool invocations is identified without consulting model text")
def _then_tool_count(state: _State) -> None:
    summary = reconstruct_trajectory(state.log_path)
    assert summary.tool_invocations == 1


@then("the iteration count is identified without consulting model text")
def _then_iter_count(state: _State) -> None:
    summary = reconstruct_trajectory(state.log_path)
    assert summary.iterations == 2


@then("every record passes schema validation")
def _then_passes_schema(state: _State, schema_loader) -> None:
    schema = schema_loader("event-log-record")
    validator = Draft202012Validator(schema)
    for record in state.log_a:
        validator.validate(record)


@then("every record carries iteration_index, stop_signal, branch_taken fields")
def _then_carries_fields(state: _State) -> None:
    for record in state.log_a:
        assert "iteration" in record
        assert "stop_signal" in record
        assert "branch_taken" in record
