"""TS-014: corrupt policy file → reject/hook_failure (FR-012, fail closed).

Why this is a separate test from policy_breach:
    The fail-closed contract says "the hook itself raised" rejects with a
    distinct ``reason_code`` so on-call sees the cause clearly. A regression
    that catches the corrupt-policy raise inside ``policy_breach`` would
    silently misclassify operational failures as business events.
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_corrupt_policy_file_rejects_with_hook_failure(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    read_jsonl,
) -> None:
    """Overwrite the policy file with garbage; expect hook_failure reject."""
    # Corrupt the snapshot the runner will read.
    policy_snapshotter.write_text("{ this is not valid json", encoding="utf-8")
    payload = json.loads((FIXTURES_DIR / "hook_failure_corrupt_policy.json").read_text())
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    assert verdict.verdict == "reject"
    assert verdict.reason_code is not None
    assert verdict.reason_code.value == "hook_failure"
    assert success is None
    assert structured is not None
    assert structured.reason_code.value == "hook_failure"
    # SC-002: zero stub calls.
    assert read_jsonl(session_tmpdir / "refund_api_calls.jsonl") == []
    # Hook failure escalates with its own reason.
    events = read_jsonl(session_tmpdir / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert len(escalations) == 1
    assert escalations[0]["payload"]["escalation_reason"] == "hook_failure"
