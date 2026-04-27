"""TS-015: policy file rewritten mid-invocation; verdict pinned to entry snapshot.

Why this scenario matters:
    The runner reads ``config/policy.json`` once at invocation entry. If a
    concurrent process rewrites the file between that read and any later
    audit-log write, the verdict and the escalation event MUST still cite
    the snapshot version that was *evaluated against*, not the current
    on-disk version. This test simulates the race by rewriting the file
    AFTER ``run_once`` returns and confirming the recorded snapshot version
    matches what the verdict claims.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_policy_overwrite_after_evaluation_does_not_change_verdict_record(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    read_jsonl,
) -> None:
    """Verdict + escalation record agree on the entry-time snapshot version."""
    # Run once under v1 (max_refund=500.00, amount=250.00 → allow).
    payload = json.loads((FIXTURES_DIR / "concurrent_policy_update.json").read_text())
    verdict, _structured, _success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )

    # Rewrite the policy file to v2 AFTER the evaluation. The audit log
    # already has the verdict for v1; this rewrite must NOT retroactively
    # mutate that record.
    policy_snapshotter.write_text(
        json.dumps(
            {
                "policy_id": "refund-policy",
                "policy_snapshot_version": "v2",
                "max_refund": "100.00",
                "comparison_stance": "strict_less_than",
                "escalation_pathway": "refund-review-queue",
                "effective_from": datetime(2026, 4, 27, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    events = read_jsonl(session_tmpdir / "events.jsonl")
    verdict_records = [e for e in events if e["kind"] == "verdict"]
    assert len(verdict_records) == 1
    assert verdict_records[0]["payload"]["policy_snapshot_version"] == "v1"
    assert verdict.policy_snapshot_version == "v1"
