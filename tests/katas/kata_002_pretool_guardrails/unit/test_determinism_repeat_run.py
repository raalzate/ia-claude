"""TS-006: identical input → byte-equal verdict (excluding evaluated_at).

Why exclude evaluated_at:
    The verdict timestamps the moment of evaluation; two evaluations a
    millisecond apart are still ``deterministic`` in the sense the spec
    means — same input → same decision. Stripping the only non-deterministic
    field reveals the actual contract under test.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from katas.kata_002_pretool_guardrails.hook import RefundPolicyHook
from katas.kata_002_pretool_guardrails.models import PolicyConfig, ToolCallPayload


def _policy() -> PolicyConfig:
    return PolicyConfig(
        policy_id="refund-policy",
        policy_snapshot_version="v1",
        max_refund=Decimal("500.00"),
        comparison_stance="strict_less_than",
        escalation_pathway="refund-review-queue",
        effective_from=datetime(2026, 4, 23, tzinfo=UTC),
    )


def _payload() -> ToolCallPayload:
    return ToolCallPayload(
        tool_name="process_refund",
        correlation_id="33333333-3333-4333-8333-333333333333",
        amount=Decimal("750.00"),
        currency="USD",
        customer_id="C-1003",
        reason="determinism test",
    )


def test_two_evaluations_yield_byte_equal_verdicts_modulo_evaluated_at() -> None:
    """Two ``evaluate`` calls produce identical JSON modulo ``evaluated_at``."""
    hook = RefundPolicyHook()
    policy = _policy()
    payload = _payload()

    first = hook.evaluate(payload, policy).model_dump(mode="json")
    second = hook.evaluate(payload, policy).model_dump(mode="json")

    first.pop("evaluated_at")
    second.pop("evaluated_at")
    assert first == second
    assert first["verdict"] == "reject"
    assert first["reason_code"] == "policy_breach"
