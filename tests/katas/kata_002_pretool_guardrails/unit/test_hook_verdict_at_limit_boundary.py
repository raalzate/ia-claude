"""TS-013: amount EXACTLY at the limit rejects under strict_less_than (D-008)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from katas.kata_002_pretool_guardrails.hook import RefundPolicyHook
from katas.kata_002_pretool_guardrails.models import PolicyConfig, ToolCallPayload


def test_amount_equal_to_max_refund_rejects_with_policy_breach() -> None:
    """``amount == max_refund`` MUST reject (strict_less_than stance)."""
    hook = RefundPolicyHook()
    policy = PolicyConfig(
        policy_id="refund-policy",
        policy_snapshot_version="v1",
        max_refund=Decimal("500.00"),
        comparison_stance="strict_less_than",
        escalation_pathway="refund-review-queue",
        effective_from=datetime(2026, 4, 23, tzinfo=UTC),
    )
    payload = ToolCallPayload(
        tool_name="process_refund",
        correlation_id="22222222-2222-4222-8222-222222222222",
        amount=Decimal("500.00"),
        currency="USD",
        customer_id="C-1002",
        reason="boundary",
    )
    verdict = hook.evaluate(payload, policy)
    assert verdict.verdict == "reject"
    assert verdict.reason_code is not None
    assert verdict.reason_code.value == "policy_breach"
