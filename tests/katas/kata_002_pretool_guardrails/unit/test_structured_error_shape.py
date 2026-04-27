"""TS-004 / TS-018: StructuredError carries every required field.

Why this is a separate test from TS-003:
    TS-003 asserts the verdict shape; TS-004 asserts the model-facing
    StructuredError shape. The two are joined by ``correlation_id`` but
    their schemas are different — making the assertion sets independent
    keeps regressions bisectable to the offending object.
"""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_structured_error_has_all_required_fields(
    policy_snapshotter: Path,
    session_tmpdir: Path,
) -> None:
    """Every required FR-003/FR-005 field is populated and deterministic."""
    payload = json.loads((FIXTURES_DIR / "over_limit.json").read_text())
    verdict, structured, _success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )

    assert structured is not None
    assert structured.verdict == "reject"
    assert structured.reason_code.value == "policy_breach"
    assert structured.field == "amount"
    assert structured.rule_violated == "less_than_max_refund"
    assert structured.policy_id == "refund-policy"
    assert structured.policy_snapshot_version == "v1"
    assert structured.correlation_id == verdict.correlation_id
    assert structured.escalation_pathway == "refund-review-queue"
    # Message is deterministic English: built from the structured fields,
    # not free text. Sanity-check it contains the policy snapshot version
    # so a regression that drops the version from the message is caught.
    assert "v1" in structured.message
    assert "refund-policy" in structured.message
