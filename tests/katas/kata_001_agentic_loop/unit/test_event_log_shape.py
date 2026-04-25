"""EventRecord JSON-schema conformance + termination-cause uniqueness.

Why this exists alongside the pydantic model: the model enforces shape in
memory; the JSON Schema enforces shape on disk. Two independent layers, one
truth — if either drifts, this test catches the mismatch (Principle II).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import validate

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry

SCHEMA_PATH = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "001-agentic-loop"
    / "contracts"
    / "event-log-record.schema.json"
)
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


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


@pytest.fixture
def schema() -> dict:
    return json.loads(SCHEMA_PATH.read_text())


@pytest.mark.parametrize(
    "fixture_name,expected_termination",
    [
        ("happy_path", "end_turn"),
        ("max_tokens", "max_tokens"),
        ("unknown_signal", "unhandled_signal"),
        ("absent_signal", "absent_signal"),
        ("decoy_phrase", "end_turn"),
    ],
)
def test_every_record_validates_against_schema(
    tmp_path, schema, fixture_name, expected_termination
):
    registry = _registry()
    session = RuntimeSession(
        model="claude-test",
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=tmp_path,
    )
    client = RecordedClient(FIXTURES / f"{fixture_name}.json")
    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)

    records = [json.loads(line) for line in session.event_log.path.read_text().splitlines() if line]
    for r in records:
        validate(instance=r, schema=schema)

    terminal = [r for r in records if r["termination_cause"] is not None]
    # SC-006: exactly one record carries a termination_cause.
    assert len(terminal) == 1
    assert terminal[0]["termination_cause"] == expected_termination
