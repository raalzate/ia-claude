"""``PreToolUseHook`` protocol + ``RefundPolicyHook`` concrete implementation.

Why this module is the pivot of the kata:
    Every other module — models, policy loader, audit log, escalation
    emitter, refund stub, runner — exists to feed or consume the verdict
    this hook produces. The hook is the deterministic boundary that
    separates *what the model proposed* from *what the system will do*.

Decision order (FR-002, FR-003, FR-005, FR-006, FR-012):
    1. Validate the payload with ``ToolCallPayload.model_validate``. Any
       pydantic ``ValidationError`` → ``schema_violation`` reject (no API
       call, no escalation per D-007).
    2. Compare ``amount < policy.max_refund`` under the declared
       ``strict_less_than`` stance (D-008). Failure → ``policy_breach``
       reject (no API call; escalation emitted by the runner).
    3. Any uncaught exception in steps 1–2 (or the policy itself fails to
       load) → ``hook_failure`` reject (no API call; escalation emitted).
    4. Otherwise → ``allow``; the runner dispatches to the refund stub.

Why fail-closed in step 3 (FR-012):
    Silent fail-open on hook errors would re-introduce exactly the gap the
    kata closes — an agent runtime that says "the hook didn't object" when
    the hook never had a chance to evaluate. Constitution Principle VI
    (Human-in-the-Loop) makes the choice explicit: when in doubt, escalate.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol

from pydantic import ValidationError

from .errors import ReasonCode
from .models import HookVerdict, PolicyConfig, ToolCallPayload
from .policy import PolicyLoadError, load_policy


class PreToolUseHook(Protocol):
    """Marker protocol for any hook that runs before tool dispatch.

    Why a protocol: Constitution Principle II demands typed boundaries. A
    future kata (e.g. kata 4 subagent isolation, kata 7 plan-mode) may
    introduce additional ``PreToolUseHook`` implementations; pinning the
    contract here keeps every implementation interchangeable.
    """

    def evaluate(
        self,
        payload: dict[str, Any] | ToolCallPayload,
        policy: PolicyConfig,
    ) -> HookVerdict:
        """Return a deterministic ``HookVerdict`` for this invocation."""
        ...


class RefundPolicyHook:
    """Concrete ``PreToolUseHook`` implementation for ``process_refund``.

    Why a class instead of a free function: the kata-7 subagent isolation
    work will compose hooks; a class makes ``RefundPolicyHook`` a stable
    object the orchestrator can hold and re-use across invocations without
    leaking state (the class itself is stateless — every ``evaluate`` call
    is independent, which is exactly what FR-010 / determinism requires).
    """

    def evaluate(
        self,
        payload: dict[str, Any] | ToolCallPayload,
        policy: PolicyConfig,
    ) -> HookVerdict:
        """Apply the three-step decision pipeline.

        Why ``payload`` accepts both shapes:
            The runner hands in raw dict (from JSON) so the hook itself owns
            the schema gate. Tests that already have a ``ToolCallPayload``
            instance pass it through; the model is frozen, so re-validation
            is a no-op-ish round trip and the test reads naturally.
        """
        # Resolve the correlation id eagerly — the verdict needs it even on
        # schema_violation paths where ``payload`` may not have parsed yet.
        # This is a defensive read: ``.get`` on dict, ``.correlation_id`` on
        # the typed model, fall back to a literal sentinel if absent.
        correlation_id = self._best_effort_correlation_id(payload)
        evaluated_at = datetime.now(tz=UTC)
        try:
            # Step 1 — schema gate.
            if isinstance(payload, ToolCallPayload):
                typed = payload
            else:
                try:
                    typed = ToolCallPayload.model_validate(payload)
                except ValidationError as exc:
                    return self._reject_schema_violation(
                        correlation_id=correlation_id,
                        policy=policy,
                        evaluated_at=evaluated_at,
                        validation_error=exc,
                    )

            # Step 2 — policy gate (strict_less_than per D-008).
            if typed.amount < policy.max_refund:
                return HookVerdict(
                    verdict="allow",
                    reason_code=None,
                    correlation_id=typed.correlation_id,
                    policy_id=policy.policy_id,
                    policy_snapshot_version=policy.policy_snapshot_version,
                    evaluated_at=evaluated_at,
                    offending_field=None,
                    offending_value=None,
                )
            return HookVerdict(
                verdict="reject",
                reason_code=ReasonCode.POLICY_BREACH,
                correlation_id=typed.correlation_id,
                policy_id=policy.policy_id,
                policy_snapshot_version=policy.policy_snapshot_version,
                evaluated_at=evaluated_at,
                offending_field="amount",
                offending_value=str(typed.amount),
            )
        except Exception:  # noqa: BLE001 — fail-closed catch-all is the contract
            # Step 3 — unhandled exception → hook_failure (FR-012).
            return self._reject_hook_failure(
                correlation_id=correlation_id,
                policy=policy,
                evaluated_at=evaluated_at,
            )

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _best_effort_correlation_id(payload: object) -> str:
        """Pull a correlation id even from malformed payloads.

        Why: schema_violation rejects still need a correlation id so the
        audit log entry can be joined to the model turn that produced the
        bad payload. If the field is missing or non-string, fall back to a
        synthetic ``unknown-*`` id; the verdict still validates because the
        ``HookVerdict`` field requires only ``min_length=1``.
        """
        if isinstance(payload, ToolCallPayload):
            return payload.correlation_id
        if isinstance(payload, dict):
            candidate = payload.get("correlation_id")
            if isinstance(candidate, str) and candidate:
                return candidate
        return "unknown-correlation-id"

    def _reject_schema_violation(
        self,
        *,
        correlation_id: str,
        policy: PolicyConfig,
        evaluated_at: datetime,
        validation_error: ValidationError,
    ) -> HookVerdict:
        """Build a ``schema_violation`` reject verdict from a pydantic error."""
        # Pull the first offending field from the ValidationError details so
        # the verdict and downstream StructuredError carry a useful path.
        first_error = validation_error.errors()[0] if validation_error.errors() else {}
        loc = first_error.get("loc", ("$",))
        field = ".".join(str(part) for part in loc) if loc else "$"
        offending_value = first_error.get("input")
        return HookVerdict(
            verdict="reject",
            reason_code=ReasonCode.SCHEMA_VIOLATION,
            correlation_id=correlation_id,
            policy_id=policy.policy_id,
            policy_snapshot_version=policy.policy_snapshot_version,
            evaluated_at=evaluated_at,
            offending_field=field or "$",
            offending_value=None if offending_value is None else str(offending_value),
        )

    def _reject_hook_failure(
        self,
        *,
        correlation_id: str,
        policy: PolicyConfig,
        evaluated_at: datetime,
    ) -> HookVerdict:
        """Build a fail-closed ``hook_failure`` verdict."""
        return HookVerdict(
            verdict="reject",
            reason_code=ReasonCode.HOOK_FAILURE,
            correlation_id=correlation_id,
            policy_id=policy.policy_id,
            policy_snapshot_version=policy.policy_snapshot_version,
            evaluated_at=evaluated_at,
            offending_field="$",
            offending_value=None,
        )


# ---------------------------------------------------------------------------
# Convenience: evaluate with policy-load fail-closed on top.
# ---------------------------------------------------------------------------


def evaluate_with_policy_path(
    *,
    hook: RefundPolicyHook,
    payload: dict[str, Any] | ToolCallPayload,
    policy_path: str,
) -> tuple[HookVerdict, PolicyConfig | None]:
    """Load the policy fresh and evaluate; on load failure, fail closed.

    Why a top-level wrapper: the hook itself can only fail-close on
    exceptions raised *inside* ``evaluate``. The policy file load happens
    *before* ``evaluate``, so the wrapper handles ``PolicyLoadError`` and
    synthesizes a ``hook_failure`` verdict using a sentinel policy id /
    version (the real values are unknown — the file failed to parse).

    Returns the verdict and the loaded policy (or ``None`` on load
    failure) so the runner can decide which escalation arguments are
    available.
    """
    correlation_id = RefundPolicyHook._best_effort_correlation_id(payload)
    evaluated_at = datetime.now(tz=UTC)
    try:
        policy = load_policy(policy_path)
    except PolicyLoadError:
        verdict = HookVerdict(
            verdict="reject",
            reason_code=ReasonCode.HOOK_FAILURE,
            correlation_id=correlation_id,
            policy_id="unknown",
            policy_snapshot_version="unknown",
            evaluated_at=evaluated_at,
            offending_field="$",
            offending_value=None,
        )
        return verdict, None
    return hook.evaluate(payload, policy), policy


__all__ = [
    "PreToolUseHook",
    "RefundPolicyHook",
    "evaluate_with_policy_path",
]


# Decimal is imported above only to keep the amount-path import surface
# discoverable from this module — the lint test asserts no float() in
# hook/models/runner, so listing Decimal here documents what is allowed.
_ = Decimal
