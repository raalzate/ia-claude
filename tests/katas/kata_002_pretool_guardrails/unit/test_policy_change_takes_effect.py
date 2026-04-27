"""TS-009 / TS-011: edit policy.json from L1 to L2; next call rejects.

Why this is the kata's operational story:
    The previous tests pin "the rule is enforced" and "the rule's value is
    not in the prompt". This test pins "the rule's value is editable
    without code, schema, or prompt change" — the third leg of the kata's
    triangle. A regression that caches the policy across invocations would
    silently make every "live" policy edit invisible to the next call.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def _write_policy(path: Path, version: str, limit: str) -> None:
    path.write_text(
        json.dumps(
            {
                "policy_id": "refund-policy",
                "policy_snapshot_version": version,
                "max_refund": limit,
                "comparison_stance": "strict_less_than",
                "escalation_pathway": "refund-review-queue",
                "effective_from": datetime(2026, 4, 23, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )


def test_lowering_max_refund_rejects_previously_allowed_amount(
    policy_snapshotter: Path,
    session_tmpdir: Path,
) -> None:
    """A=300 allowed under L1=500; rejected under L2=200 with new snapshot version."""
    _write_policy(policy_snapshotter, version="L1", limit="500.00")
    payload_before = json.loads((FIXTURES_DIR / "policy_change_before.json").read_text())
    verdict_before, _struct, _success = run_once(
        payload_dict=payload_before,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir / "before",
    )
    assert verdict_before.verdict == "allow"
    assert verdict_before.policy_snapshot_version == "L1"

    # Lower the limit on disk. No code, prompt, or schema change.
    _write_policy(policy_snapshotter, version="L2", limit="200.00")
    payload_after = json.loads((FIXTURES_DIR / "policy_change_after.json").read_text())
    verdict_after, struct_after, _success_after = run_once(
        payload_dict=payload_after,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir / "after",
    )
    assert verdict_after.verdict == "reject"
    assert verdict_after.reason_code is not None
    assert verdict_after.reason_code.value == "policy_breach"
    assert verdict_after.policy_snapshot_version == "L2"
    assert struct_after is not None
    assert struct_after.policy_snapshot_version == "L2"
