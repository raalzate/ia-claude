"""Schema validation of every emitted ``EventRecord``.

Why: SC-008 says the event log alone is the source of truth. If even one
record is off-schema, downstream replay / reconstruction silently breaks.
This test runs the canonical happy-path fixture and validates every line
against ``contracts/event-log-record.schema.json``.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from jsonschema import Draft202012Validator

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession


def _session_with_fixture(name: str, runs_dir: Path) -> RuntimeSession:
    fixture = Path(__file__).resolve().parents[1] / "fixtures" / f"{name}.json"
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
    return RuntimeSession.open(
        session_id=str(uuid.uuid4()),
        model="claude-test",
        client=RecordedClient.from_fixture(fixture),
        runs_root=runs_dir,
        tool_definitions=[(definition, lambda payload: {"city": payload["city"], "temp_c": 18})],
    )


def test_every_record_validates(runs_dir: Path, schema_loader) -> None:
    schema = schema_loader("event-log-record")
    validator = Draft202012Validator(schema)
    session = _session_with_fixture("happy_path", runs_dir)
    run(session, "weather please")
    session.close()
    records = [
        json.loads(line)
        for line in session.event_log.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert records, "happy_path produced no events — fixture wired wrong"
    for record in records:
        validator.validate(record)


def test_exactly_one_terminal_record(runs_dir: Path) -> None:
    """``termination_cause`` populated on exactly one line per run (FR-009)."""
    session = _session_with_fixture("happy_path", runs_dir)
    run(session, "weather please")
    session.close()
    records = [
        json.loads(line)
        for line in session.event_log.path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    terminal = [r for r in records if r.get("termination_cause")]
    assert len(terminal) == 1
