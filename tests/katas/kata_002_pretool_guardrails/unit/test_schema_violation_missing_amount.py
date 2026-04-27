"""TS-012 / TS-022: missing amount → schema_violation, zero stub calls."""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_missing_amount_field_rejects_as_schema_violation(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    read_jsonl,
) -> None:
    payload = json.loads((FIXTURES_DIR / "missing_amount.json").read_text())
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    assert verdict.verdict == "reject"
    assert verdict.reason_code is not None
    assert verdict.reason_code.value == "schema_violation"
    assert success is None
    assert structured is not None
    # SC-002: zero stub calls.
    assert read_jsonl(session_tmpdir / "refund_api_calls.jsonl") == []
    # D-007: schema_violation does NOT escalate.
    events = read_jsonl(session_tmpdir / "events.jsonl")
    assert all(e["kind"] != "escalation" for e in events)
