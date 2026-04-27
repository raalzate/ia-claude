"""TS-005 / TS-020: EscalationEvent.actions_taken == [] and reason matches verdict."""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_escalation_event_actions_taken_empty(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    read_jsonl,
) -> None:
    """The escalation event records zero actions on a pre-call block."""
    payload = json.loads((FIXTURES_DIR / "over_limit.json").read_text())
    run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    events = read_jsonl(session_tmpdir / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert len(escalations) == 1
    payload_record = escalations[0]["payload"]
    assert payload_record["escalation_reason"] == "policy_breach"
    assert payload_record["actions_taken"] == []
    assert payload_record["routing_target"] == "refund-review-queue"
    # SHA-256 lowercase hex digest pattern.
    assert len(payload_record["rejected_payload_digest"]) == 64
    assert all(c in "0123456789abcdef" for c in payload_record["rejected_payload_digest"])
