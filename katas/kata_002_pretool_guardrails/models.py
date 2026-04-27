"""Pydantic v2 boundary models for kata 2 (PreToolUse guardrails).

Why every boundary is a typed model:
    Constitution Principle II (Schema-Enforced Boundaries, NN) — the only
    structural defense against the prompt-only-enforcement anti-pattern is to
    refuse to *let* an unstructured payload reach the refund API at all. The
    SDK dispatches a tool call only after the hook produces a HookVerdict
    whose schema is verified end-to-end (see ``contracts/`` for the JSON
    Schema mirrors that pin these contracts at the kata boundary).

The five models below mirror, 1:1, the schemas under
``specs/002-pretool-guardrails/contracts/``. Field types intentionally use
``Decimal`` (not ``float``) for the amount path — see Principle I and the
``test_no_float_in_amount_path.py`` AST lint.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .errors import ReasonCode

# ---------------------------------------------------------------------------
# ToolCallPayload
# ---------------------------------------------------------------------------


class ToolCallPayload(BaseModel):
    """The typed input the agent sends to ``process_refund``.

    Why ``extra="forbid"``: spec §Edge Cases declares the strict stance — an
    unexpected field is a schema violation, not silently ignored. Without
    this, the model could embed prose instructions inside an unknown field
    and re-introduce the prompt-only anti-pattern through the side door.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_name: Literal["process_refund"]
    correlation_id: str = Field(min_length=1)
    amount: Decimal
    currency: Literal["USD"]
    customer_id: str = Field(min_length=1)
    reason: str | None = None

    @field_validator("amount", mode="before")
    @classmethod
    def _reject_float_amount(cls, v: object) -> object:
        """Reject ``float``/``bool`` amounts at parse time.

        Why: ``Decimal(0.1)`` is ``0.1000000000000000055511151231257827021181583404541015625``;
        accepting a float here would make the policy threshold comparison
        non-deterministic at the boundary. JSON schemas express the amount
        as a string for the same reason — see ``contracts/tool-call-payload.schema.json``.
        ``bool`` is a subclass of ``int`` in Python, so guard it explicitly
        (the ``edge_cases.feature`` outline includes a boolean-amount row).
        """
        if isinstance(v, bool) or isinstance(v, float):
            raise ValueError("amount must be a Decimal-safe string or int, not float/bool")
        return v

    @field_validator("amount")
    @classmethod
    def _amount_must_be_positive(cls, v: Decimal) -> Decimal:
        """Enforce ``amount > 0`` (FR-002)."""
        if v <= 0:
            raise ValueError("amount must be strictly positive")
        return v


# ---------------------------------------------------------------------------
# PolicyConfig
# ---------------------------------------------------------------------------


class PolicyConfig(BaseModel):
    """Externally-configurable refund policy snapshot.

    Why frozen: a single invocation MUST evaluate against exactly one
    snapshot (spec §Edge Cases — concurrent policy update). Freezing the
    instance prevents accidental in-process mutation that would let a later
    branch see a different limit than the verdict claims to have evaluated.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy_id: str = Field(min_length=1)
    policy_snapshot_version: str = Field(min_length=1)
    max_refund: Decimal
    comparison_stance: Literal["strict_less_than"]
    escalation_pathway: str = Field(min_length=1)
    effective_from: datetime

    @field_validator("max_refund", mode="before")
    @classmethod
    def _reject_float_max_refund(cls, v: object) -> object:
        """Same reasoning as ``ToolCallPayload._reject_float_amount``."""
        if isinstance(v, bool) or isinstance(v, float):
            raise ValueError("max_refund must be a Decimal-safe string, not float/bool")
        return v


# ---------------------------------------------------------------------------
# HookVerdict
# ---------------------------------------------------------------------------


class HookVerdict(BaseModel):
    """The deterministic allow/reject decision produced by RefundPolicyHook.

    Why determinism is encoded in the type:
        Same ``(payload, policy_snapshot)`` → same ``HookVerdict`` (FR-010,
        SC-001) — the only field allowed to differ across two evaluations of
        the same input is ``evaluated_at``. ``test_determinism_repeat_run.py``
        excludes that single field and asserts byte-equality.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: Literal["allow", "reject"]
    reason_code: ReasonCode | None = None
    correlation_id: str = Field(min_length=1)
    policy_id: str = Field(min_length=1)
    policy_snapshot_version: str = Field(min_length=1)
    evaluated_at: datetime
    offending_field: str | None = None
    offending_value: str | None = None


# ---------------------------------------------------------------------------
# StructuredError
# ---------------------------------------------------------------------------


class StructuredError(BaseModel):
    """The machine-parseable rejection object handed back to the model.

    Why this is the ONLY rejection shape:
        FR-005 — free-text apology from the tool channel is forbidden. Free
        text would let the model "interpret" the rejection and try again
        with paraphrased intent (this is exactly the prompt-only-enforcement
        anti-pattern). A structured error confines the model to either
        (a) replying to the user that the action was blocked, or
        (b) proposing a different, structured action.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    verdict: Literal["reject"] = "reject"
    reason_code: ReasonCode
    field: str = Field(min_length=1)
    rule_violated: str = Field(min_length=1)
    policy_id: str | None = None
    policy_snapshot_version: str | None = None
    correlation_id: str = Field(min_length=1)
    escalation_pathway: str = Field(min_length=1)
    message: str = Field(min_length=1)


# ---------------------------------------------------------------------------
# EscalationEvent
# ---------------------------------------------------------------------------


class EscalationEvent(BaseModel):
    """Durable record emitted on policy_breach / hook_failure rejects only.

    Why ``actions_taken`` is always ``[]``:
        FR-006 / SC-002 — the whole point of pre-call blocking is that no
        action was taken. The field is preserved for shape parity with
        Principle VI's typed escalation payload so a generic reviewer UI can
        consume the event without special-casing pre-call blocks.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["escalation"] = "escalation"
    correlation_id: str = Field(min_length=1)
    emitted_at: datetime
    policy_id: str = Field(min_length=1)
    policy_snapshot_version: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    actions_taken: list[str] = Field(default_factory=list, max_length=0)
    escalation_reason: Literal["policy_breach", "hook_failure"]
    routing_target: str = Field(min_length=1)
    rejected_payload_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
