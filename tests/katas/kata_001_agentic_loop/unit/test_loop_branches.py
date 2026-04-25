"""Unit tests for every stop_signal branch of `loop.run`.

Why these are unit tests (not BDD): the BDD suite proves end-to-end behavior
against recorded sessions, which is slower and noisier. Branch tests pin down
the loop's switch by feeding it synthetic Turn objects directly — fast, surgical.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def _registry_with_get_weather() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="get_weather",
            description="Look up the current weather for a city.",
            input_schema={
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
                "additionalProperties": False,
            },
        ),
        handler=lambda payload: {"temp_c": 18, "city": payload["city"]},
    )
    return registry


def _make_session(tmp_path, registry: ToolRegistry) -> RuntimeSession:
    return RuntimeSession(
        model="claude-test",
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=tmp_path,
    )


def _read_jsonl(path: Path) -> list[dict]:
    import json

    return [json.loads(line) for line in path.read_text().splitlines() if line]


def test_end_turn_terminates_loop(tmp_path) -> None:
    from katas.kata_001_agentic_loop.loop import run

    registry = _registry_with_get_weather()
    session = _make_session(tmp_path, registry)
    client = RecordedClient(FIXTURES / "happy_path.json")

    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)

    assert result == "end_turn"
    records = _read_jsonl(session.event_log.path)
    terminal = [r for r in records if r["termination_cause"] is not None]
    assert len(terminal) == 1
    assert terminal[0]["termination_cause"] == "end_turn"
    assert terminal[0]["branch_taken"] == "terminate"


def test_tool_use_dispatches_then_continues(tmp_path) -> None:
    from katas.kata_001_agentic_loop.loop import run

    registry = _registry_with_get_weather()
    session = _make_session(tmp_path, registry)
    client = RecordedClient(FIXTURES / "happy_path.json")

    run(session=session, client=client, initial_user_message="hi")
    session.close(termination="end_turn")

    records = _read_jsonl(session.event_log.path)
    assert any(
        r["branch_taken"] == "tool_dispatch" and r["tool_name"] == "get_weather"
        for r in records
    )


def test_max_tokens_halts_with_label(tmp_path) -> None:
    from katas.kata_001_agentic_loop.loop import run

    registry = _registry_with_get_weather()
    session = _make_session(tmp_path, registry)
    client = RecordedClient(FIXTURES / "max_tokens.json")

    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    assert result == "max_tokens"
    records = _read_jsonl(session.event_log.path)
    assert records[-1]["termination_cause"] == "max_tokens"
    assert records[-1]["branch_taken"] == "terminate"


def test_unknown_signal_halts_unhandled(tmp_path) -> None:
    from katas.kata_001_agentic_loop.loop import run

    registry = _registry_with_get_weather()
    session = _make_session(tmp_path, registry)
    client = RecordedClient(FIXTURES / "unknown_signal.json")

    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    assert result == "unhandled_signal"
    records = _read_jsonl(session.event_log.path)
    assert records[-1]["branch_taken"] == "halt_unhandled"
    assert records[-1]["termination_cause"] == "unhandled_signal"


def test_absent_signal_halts_protocol_violation(tmp_path) -> None:
    from katas.kata_001_agentic_loop.loop import run

    registry = _registry_with_get_weather()
    session = _make_session(tmp_path, registry)
    client = RecordedClient(FIXTURES / "absent_signal.json")

    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    assert result == "absent_signal"
    records = _read_jsonl(session.event_log.path)
    assert records[-1]["termination_cause"] == "absent_signal"
    assert records[-1]["branch_taken"] == "halt_unhandled"


def test_stop_sequence_branch_handled(tmp_path) -> None:
    """stop_sequence is part of the StopSignal Literal — the loop must label it."""
    from katas.kata_001_agentic_loop.loop import run

    fixture = tmp_path / "stop_sequence.json"
    fixture.write_text(
        '{"responses": [{"id": "msg_ss", "stop_reason": "stop_sequence", '
        '"content": [{"type": "text", "text": "stopped on sequence"}]}]}'
    )
    registry = _registry_with_get_weather()
    session = _make_session(tmp_path / "run", registry)
    client = RecordedClient(fixture)

    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    assert result == "stop_sequence"
    records = _read_jsonl(session.event_log.path)
    assert records[-1]["termination_cause"] == "stop_sequence"
