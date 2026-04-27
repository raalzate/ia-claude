"""Reason-code enum used across HookVerdict, StructuredError, EscalationEvent.

Why an explicit enum:
    Constitution Principle II (Schema-Enforced Boundaries, NN) requires
    enumerations to include explicit values; the three values below correspond
    1:1 to the three rejection paths the hook must distinguish:

    * ``schema_violation`` — payload failed pydantic validation (client bug).
      Does NOT escalate (FR-007 carve-out, D-007).
    * ``policy_breach`` — payload was well-formed but ``amount`` was not
      strictly less than ``PolicyConfig.max_refund`` (business event). DOES
      escalate (Principle VI).
    * ``hook_failure`` — the hook itself raised before producing a verdict
      (e.g. corrupt ``config/policy.json``). Fails CLOSED per FR-012; DOES
      escalate, but with a distinct cause that points to operations rather
      than the model.
"""

from __future__ import annotations

from enum import StrEnum


class ReasonCode(StrEnum):
    """Reasons a HookVerdict may be ``reject``."""

    SCHEMA_VIOLATION = "schema_violation"
    POLICY_BREACH = "policy_breach"
    HOOK_FAILURE = "hook_failure"


ESCALATING_REASON_CODES: frozenset[ReasonCode] = frozenset(
    {ReasonCode.POLICY_BREACH, ReasonCode.HOOK_FAILURE}
)
"""The narrower set of reason codes that emit an EscalationEvent.

Why narrower than ReasonCode itself: schema_violation is a client-side bug —
the model produced a malformed payload — so the right escalation pathway is
``client_fix_required`` (re-prompt the model) rather than queueing for human
review. See data-model.md and D-007 for the rationale.
"""
