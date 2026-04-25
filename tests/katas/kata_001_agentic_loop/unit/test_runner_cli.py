"""Smoke tests for the runner CLI.

Why a smoke test (not a full CLI matrix): the runner is a wiring thin: arg
parsing → session construction → run → summary print. The end-to-end logic
is already covered by the loop tests; this just verifies the wiring works
and the JSON summary is parseable.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from katas.kata_001_agentic_loop.runner import main

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_runner_against_recorded_fixture(tmp_path):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = main(
            [
                "--model",
                "claude-test",
                "--prompt",
                "hi",
                "--fixture",
                str(FIXTURES / "happy_path.json"),
                "--runs-root",
                str(tmp_path),
            ]
        )
    assert rc == 0
    summary = json.loads(buf.getvalue())
    assert summary["termination_cause"] == "end_turn"
    assert summary["iterations"] == 2
    assert summary["tool_invocations"] == 1
    assert Path(summary["events_jsonl"]).exists()


def test_runner_requires_fixture_or_live(tmp_path, monkeypatch):
    monkeypatch.delenv("LIVE_API", raising=False)
    try:
        main(["--runs-root", str(tmp_path)])
    except SystemExit as exc:
        assert "fixture" in str(exc.code) or exc.code != 0
        return
    raise AssertionError("expected SystemExit when neither fixture nor LIVE_API supplied")
