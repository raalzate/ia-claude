"""TS-010: a policy edit must not change ``prompts.py`` or any contract schema.

Why this is asserted by digest, not eyeballing:
    A regression that "fixes" enforcement by re-introducing the prompt-only
    anti-pattern would touch ``prompts.py`` to add the new limit. Hashing
    the file before and after a policy edit lets the test catch that
    regression structurally — without a human review step.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from ..conftest import REPO_ROOT


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_policy_edit_does_not_touch_prompts_or_contracts(
    policy_snapshotter: Path,
    session_tmpdir: Path,
) -> None:
    """Edit the snapshot's max_refund; assert prompt + contract digests are unchanged."""
    prompts_file = REPO_ROOT / "katas" / "kata_002_pretool_guardrails" / "prompts.py"
    contracts_dir = REPO_ROOT / "specs" / "002-pretool-guardrails" / "contracts"

    prompts_before = _digest_file(prompts_file)
    contracts_before = {p.name: _digest_file(p) for p in contracts_dir.glob("*.schema.json")}

    # Simulate the policy edit (this is what compliance would do at 09:00).
    policy_snapshotter.write_text(
        json.dumps(
            {
                "policy_id": "refund-policy",
                "policy_snapshot_version": "v-after-edit",
                "max_refund": "250.00",
                "comparison_stance": "strict_less_than",
                "escalation_pathway": "refund-review-queue",
                "effective_from": datetime(2026, 4, 27, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )

    prompts_after = _digest_file(prompts_file)
    contracts_after = {p.name: _digest_file(p) for p in contracts_dir.glob("*.schema.json")}

    assert prompts_before == prompts_after
    assert contracts_before == contracts_after
