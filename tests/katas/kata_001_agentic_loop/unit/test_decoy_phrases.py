"""Synthetic decoy-phrase coverage (US2 / SC-004).

Why this file even exists alongside decoy_phrase.json: the JSON fixture
proves end-to-end behavior, but a parameterized unit test makes the
"every phrase listed in SC-004 is harmless" promise loud and grep-able.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from katas.kata_001_agentic_loop.client import RecordedClient
from katas.kata_001_agentic_loop.loop import run
from katas.kata_001_agentic_loop.models import ToolDefinition
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import ToolRegistry

DECOY_PHRASES = ["task complete", "we are done", "finished", "all done"]


def _make_fixture(tmp_path: Path, text: str) -> Path:
    fixture = tmp_path / "decoy.json"
    fixture.write_text(
        json.dumps(
            {
                "responses": [
                    {
                        "id": "msg_unit_1",
                        "stop_reason": "tool_use",
                        "content": [
                            {"type": "text", "text": text},
                            {
                                "type": "tool_use",
                                "id": "toolu_unit_1",
                                "name": "echo",
                                "input": {"message": text},
                            },
                        ],
                    },
                    {
                        "id": "msg_unit_2",
                        "stop_reason": "end_turn",
                        "content": [{"type": "text", "text": "ok"}],
                    },
                ]
            }
        )
    )
    return fixture


@pytest.mark.parametrize("phrase", DECOY_PHRASES)
def test_decoy_phrase_does_not_terminate_early(tmp_path, phrase):
    registry = ToolRegistry()
    registry.register(
        ToolDefinition(
            name="echo",
            description="Echo a message back.",
            input_schema={
                "type": "object",
                "properties": {"message": {"type": "string"}},
                "required": ["message"],
                "additionalProperties": False,
            },
        ),
        handler=lambda payload: payload["message"],
    )
    session = RuntimeSession(
        model="claude-test",
        tool_definitions=registry.definitions,
        registry=registry,
        runs_root=tmp_path,
    )
    client = RecordedClient(_make_fixture(tmp_path, phrase))

    result = run(session=session, client=client, initial_user_message="hi")
    session.close(termination=result)
    assert result == "end_turn"

    records = [
        json.loads(line)
        for line in session.event_log.path.read_text().splitlines()
        if line
    ]
    # First record must be a tool_dispatch (not a premature termination on
    # any of the decoy phrases above).
    assert records[0]["branch_taken"] == "tool_dispatch"
    assert records[-1]["termination_cause"] == "end_turn"
