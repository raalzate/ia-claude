"""Smoke test for the ``runner`` CLI entrypoint.

Why: ``quickstart.md`` advertises the ``python -m katas.kata_001_agentic_loop.runner``
invocation. If anyone breaks the parser, the practitioner's first kata run
fails with an opaque traceback. This test executes ``runner.main`` against
a recorded fixture and asserts it prints the events.jsonl path on stdout.
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_001_agentic_loop import runner


def test_runner_against_recorded_fixture_succeeds(tmp_path: Path, capsys) -> None:
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    rc = runner.main(
        [
            "--prompt",
            "weather please",
            "--fixture",
            "happy_path",
            "--runs-root",
            str(runs_root),
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert rc == 0
    assert payload["termination_cause"] == "end_turn"
    assert payload["iterations"] == 2
    assert payload["tool_invocations"] == 1
    assert Path(payload["events_log"]).exists()


def test_runner_without_fixture_or_live_api_errors(tmp_path: Path, capsys) -> None:
    """``runner`` refuses to start without an explicit source — no silent default."""
    runs_root = tmp_path / "runs"
    runs_root.mkdir()
    rc = runner.main(
        [
            "--prompt",
            "weather please",
            "--runs-root",
            str(runs_root),
        ]
    )
    err = capsys.readouterr().err
    assert rc == 2
    assert "fixture" in err
