"""TS-001: in-policy refund yields HookVerdict(allow, reason_code=None).

Why this test pins behaviour:
    US1's whole point is the hook MUST NOT over-block. If a regression made
    every refund reject (e.g. a flipped comparison operator), this is the
    canary that catches it. Asserting both ``verdict`` and the absence of a
    ``reason_code`` keeps the contract tight — allow verdicts have no
    reason_code by schema invariant.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from katas.kata_002_pretool_guardrails.hook import RefundPolicyHook
from katas.kata_002_pretool_guardrails.models import PolicyConfig, ToolCallPayload


def _policy(max_refund: str = "500.00") -> PolicyConfig:
    return PolicyConfig(
        policy_id="refund-policy",
        policy_snapshot_version="v1",
        max_refund=Decimal(max_refund),
        comparison_stance="strict_less_than",
        escalation_pathway="refund-review-queue",
        effective_from=datetime(2026, 4, 23, tzinfo=UTC),
    )


def _payload(amount: str) -> ToolCallPayload:
    return ToolCallPayload(
        tool_name="process_refund",
        correlation_id="11111111-1111-4111-8111-111111111111",
        amount=Decimal(amount),
        currency="USD",
        customer_id="C-1001",
        reason="within-limit unit test",
    )


def test_hook_allows_amount_strictly_below_max_refund() -> None:
    """Amount strictly below the limit returns allow with reason_code=None."""
    hook = RefundPolicyHook()
    verdict = hook.evaluate(_payload("120.00"), _policy("500.00"))

    assert verdict.verdict == "allow"
    assert verdict.reason_code is None
    assert verdict.offending_field is None
    assert verdict.offending_value is None
    assert verdict.policy_id == "refund-policy"
    assert verdict.policy_snapshot_version == "v1"
