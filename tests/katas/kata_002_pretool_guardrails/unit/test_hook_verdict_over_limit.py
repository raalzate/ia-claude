"""TS-003 / TS-005: over-limit amount → reject/policy_breach + escalation.

Why these two specs in one file:
    They share the same fixture (over-limit payload) and assert two halves
    of the same outcome — verdict shape and audit-side effects. Pulling
    them apart would require two duplicate setups; bundling them keeps the
    "single shape of rejection" contract visible at one read.
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_over_limit_rejects_with_policy_breach_and_emits_escalation(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    read_jsonl,
) -> None:
    """over_limit.json → reject/policy_breach, zero stub calls, one escalation."""
    payload = json.loads((FIXTURES_DIR / "over_limit.json").read_text())
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )

    assert verdict.verdict == "reject"
    assert verdict.reason_code is not None
    assert verdict.reason_code.value == "policy_breach"
    assert success is None
    assert structured is not None
    assert structured.reason_code.value == "policy_breach"

    # SC-002: zero stub calls on reject.
    stub_log = read_jsonl(session_tmpdir / "refund_api_calls.jsonl")
    assert stub_log == []

    # TS-005: exactly one escalation event with policy_breach reason.
    events = read_jsonl(session_tmpdir / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert len(escalations) == 1
    assert escalations[0]["payload"]["escalation_reason"] == "policy_breach"
