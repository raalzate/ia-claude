"""TS-023: PolicyConfig is frozen + each invocation reloads a fresh instance.

Why frozen:
    A mutable PolicyConfig would let one branch of the hook see a different
    limit than the audit log records. ``frozen=True`` makes that class of
    bug impossible at runtime — the mutation raises ``ValidationError``
    before it lands.

Why reload-per-invocation:
    The kata's whole US3 story is policy-as-data. Caching the
    PolicyConfig across invocations would silently make every "live"
    policy edit invisible to the next refund call.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from katas.kata_002_pretool_guardrails.models import PolicyConfig
from katas.kata_002_pretool_guardrails.policy import load_policy


def test_policy_config_instance_is_frozen() -> None:
    """Mutating any field on a loaded PolicyConfig raises."""
    cfg = PolicyConfig(
        policy_id="refund-policy",
        policy_snapshot_version="v1",
        max_refund=Decimal("500.00"),
        comparison_stance="strict_less_than",
        escalation_pathway="refund-review-queue",
        effective_from=datetime(2026, 4, 23, tzinfo=UTC),
    )
    with pytest.raises(ValidationError):
        cfg.max_refund = Decimal("100.00")  # type: ignore[misc]


def test_two_loads_produce_distinct_instances(policy_snapshotter: Path) -> None:
    """Each call to ``load_policy`` returns a fresh object (no caching)."""
    first = load_policy(policy_snapshotter)
    second = load_policy(policy_snapshotter)
    assert first is not second
    assert first.model_dump() == second.model_dump()
