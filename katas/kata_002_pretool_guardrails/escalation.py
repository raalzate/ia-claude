"""``EscalationEvent`` emitter — writes only on policy_breach / hook_failure.

Why this module exists:
    Constitution Principle VI (Human-in-the-Loop, NN) and FR-007 require
    that *every* policy-breach reject hand off to a typed escalation
    payload with ``actions_taken=[]`` (because no action was taken — the
    hook blocked pre-call by construction). ``hook_failure`` rejects also
    escalate, but with a distinct ``escalation_reason`` so on-call sees
    "the hook itself broke" instead of "policy was breached". A
    ``schema_violation`` is a client-side bug and does NOT escalate (D-007).

Why digest, not raw payload:
    The audit log is durable — embedding the raw payload would leak PII
    every time a customer triggers a refund block. The SHA-256 digest is
    sufficient for on-call to correlate against the per-session
    ``events.jsonl`` (which holds the full payload) without persisting
    the sensitive fields outside the session window.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Literal

from .events import EventLog
from .models import EscalationEvent, HookVerdict, PolicyConfig, ToolCallPayload


def compute_payload_digest(payload: ToolCallPayload) -> str:
    """Return the lowercase-hex SHA-256 of the JSON-serialized payload.

    Why deterministic JSON: two callers handing in the same payload must
    produce the same digest. ``model_dump(mode="json")`` + ``sort_keys``
    achieves that. ``Decimal`` is rendered via ``str`` to match the schema
    contract (decimals are strings on the wire).
    """
    body = payload.model_dump(mode="json")
    body["amount"] = str(payload.amount)
    blob = json.dumps(body, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_escalation_event(
    *,
    verdict: HookVerdict,
    policy: PolicyConfig | None,
    payload: ToolCallPayload | None,
    payload_digest: str | None = None,
    reason: Literal["policy_breach", "hook_failure"],
) -> EscalationEvent:
    """Construct an ``EscalationEvent`` from the available context.

    Why this signature: on ``hook_failure`` the policy may be unloadable —
    the caller passes ``policy=None`` and ``payload=None`` and supplies a
    pre-computed digest from the raw bytes. On ``policy_breach`` both are
    available and the digest is computed here.
    """
    if reason == "policy_breach":
        if policy is None or payload is None:
            raise ValueError("policy_breach escalation requires policy and payload")
        digest = payload_digest or compute_payload_digest(payload)
        summary = (
            f"Refund of {payload.amount} {payload.currency} for customer "
            f"{payload.customer_id} blocked by policy {policy.policy_id} "
            f"{policy.policy_snapshot_version}."
        )
        return EscalationEvent(
            correlation_id=verdict.correlation_id,
            emitted_at=datetime.now(tz=UTC),
            policy_id=policy.policy_id,
            policy_snapshot_version=policy.policy_snapshot_version,
            summary=summary,
            actions_taken=[],
            escalation_reason="policy_breach",
            routing_target=policy.escalation_pathway,
            rejected_payload_digest=digest,
        )
    # hook_failure path: policy and payload may be missing — fall back to
    # the verdict's pinned policy id/version, which the hook records even
    # when it ultimately rejects with hook_failure.
    digest = payload_digest or "0" * 64
    summary = (
        f"PreToolUse hook failed internally for correlation {verdict.correlation_id}; "
        "invocation rejected fail-closed."
    )
    return EscalationEvent(
        correlation_id=verdict.correlation_id,
        emitted_at=datetime.now(tz=UTC),
        policy_id=verdict.policy_id,
        policy_snapshot_version=verdict.policy_snapshot_version,
        summary=summary,
        actions_taken=[],
        escalation_reason="hook_failure",
        routing_target="hook-failure-oncall",
        rejected_payload_digest=digest,
    )


def emit_escalation(
    log: EventLog,
    event: EscalationEvent,
) -> EscalationEvent:
    """Append the event to the JSONL audit log and return it unchanged."""
    log.append(
        kind="escalation",
        correlation_id=event.correlation_id,
        payload=event.model_dump(mode="json"),
    )
    return event
