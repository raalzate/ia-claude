"""CLI entrypoint for kata 2.

Why this module exists:
    The kata's MVP demonstration is "edit ``config/policy.json``, re-run
    one CLI command, observe the verdict change." A thin runner around
    ``RefundPolicyHook`` makes that workflow scriptable and bisectable.
    The runner is also the only place that wires together (policy load) →
    (hook evaluate) → (refund stub OR escalation emit) → (audit log).

Exit codes:
    * ``0``  — allow + stub success.
    * ``10`` — schema_violation reject.
    * ``11`` — policy_breach reject.
    * ``20`` — hook_failure reject.

Why typed exit codes: the notebook (T053 cell 6) documents these so a
practitioner running the CLI in CI knows *why* a non-zero exit happened
without parsing log files.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

from .errors import ESCALATING_REASON_CODES, ReasonCode
from .escalation import build_escalation_event, compute_payload_digest, emit_escalation
from .events import EventLog
from .hook import RefundPolicyHook, evaluate_with_policy_path
from .models import HookVerdict, PolicyConfig, StructuredError, ToolCallPayload
from .policy import DEFAULT_POLICY_PATH
from .refund_api_stub import RefundApiStub

EXIT_ALLOW = 0
EXIT_SCHEMA_VIOLATION = 10
EXIT_POLICY_BREACH = 11
EXIT_HOOK_FAILURE = 20


def _exit_code_for(verdict: HookVerdict) -> int:
    """Map verdict to CLI exit code (see module docstring for table)."""
    if verdict.verdict == "allow":
        return EXIT_ALLOW
    if verdict.reason_code == ReasonCode.SCHEMA_VIOLATION:
        return EXIT_SCHEMA_VIOLATION
    if verdict.reason_code == ReasonCode.POLICY_BREACH:
        return EXIT_POLICY_BREACH
    return EXIT_HOOK_FAILURE


def build_structured_error(
    verdict: HookVerdict,
    policy: PolicyConfig | None,
) -> StructuredError:
    """Translate a reject ``HookVerdict`` into a model-facing ``StructuredError``.

    Why this is the only path the model sees on reject (FR-005):
        Free-text apologies on the tool channel let the model paraphrase
        the rejection and re-issue an equivalent request. A typed object
        with ``reason_code`` / ``rule_violated`` keeps the next turn
        confined to "report the rejection structurally" or "propose a
        different action" — not "re-try with friendlier wording."
    """
    if verdict.verdict != "reject":
        raise ValueError("StructuredError is only emitted on reject verdicts")
    reason_code = verdict.reason_code
    assert reason_code is not None  # invariant: reject always has reason_code
    if reason_code == ReasonCode.POLICY_BREACH:
        assert policy is not None
        rule = "less_than_max_refund"
        pathway = policy.escalation_pathway
        message = (
            f"Refund rejected by policy {policy.policy_id} "
            f"{policy.policy_snapshot_version}: amount {verdict.offending_value} "
            "exceeds the configured limit. Route the customer to the escalation pathway."
        )
        return StructuredError(
            reason_code=reason_code,
            field=verdict.offending_field or "amount",
            rule_violated=rule,
            policy_id=policy.policy_id,
            policy_snapshot_version=policy.policy_snapshot_version,
            correlation_id=verdict.correlation_id,
            escalation_pathway=pathway,
            message=message,
        )
    if reason_code == ReasonCode.SCHEMA_VIOLATION:
        return StructuredError(
            reason_code=reason_code,
            field=verdict.offending_field or "$",
            rule_violated="schema_violation",
            policy_id=None,
            policy_snapshot_version=None,
            correlation_id=verdict.correlation_id,
            escalation_pathway="client_fix_required",
            message=(
                f"Refund payload rejected by schema validation "
                f"(field={verdict.offending_field}). Re-issue the call "
                "with a valid ToolCallPayload."
            ),
        )
    # hook_failure
    return StructuredError(
        reason_code=ReasonCode.HOOK_FAILURE,
        field=verdict.offending_field or "$",
        rule_violated="hook_internal_error",
        policy_id=None,
        policy_snapshot_version=None,
        correlation_id=verdict.correlation_id,
        escalation_pathway="hook-failure-oncall",
        message=(
            "PreToolUse hook failed internally; refund blocked fail-closed. "
            "On-call has been notified via the escalation event."
        ),
    )


def run_once(
    *,
    payload_dict: dict[str, Any],
    policy_path: Path,
    session_dir: Path,
) -> tuple[HookVerdict, StructuredError | None, dict[str, Any] | None]:
    """End-to-end runner for a single invocation.

    Steps:
        1. Open the per-session ``EventLog`` and the refund-API stub.
        2. Append an ``invocation`` audit record (the raw payload, before
           any validation — Principle VII demands provenance even for
           malformed payloads).
        3. Load policy + evaluate hook (fail-closed wrapper).
        4. On allow: dispatch to the stub, append verdict + refund_api_call
           records, return success body.
        5. On reject: build the StructuredError, append the verdict
           record, emit an EscalationEvent iff the reason escalates.
    """
    log = EventLog(Path(session_dir))
    stub = RefundApiStub(log_path=log.session_dir / "refund_api_calls.jsonl")
    correlation_id = (
        payload_dict.get("correlation_id")
        if isinstance(payload_dict.get("correlation_id"), str)
        and payload_dict["correlation_id"]
        else f"unknown-{uuid.uuid4()}"
    )

    log.append(
        kind="invocation",
        correlation_id=correlation_id,
        payload=payload_dict,
    )

    hook = RefundPolicyHook()
    verdict, policy = evaluate_with_policy_path(
        hook=hook,
        payload=payload_dict,
        policy_path=str(policy_path),
    )

    log.append(
        kind="verdict",
        correlation_id=verdict.correlation_id,
        payload=verdict.model_dump(mode="json"),
    )

    if verdict.verdict == "allow":
        # Re-validate at the boundary — the stub MUST receive a typed
        # ``ToolCallPayload``, never the raw dict, so a malformed payload
        # cannot silently flow through (the hook would have rejected it,
        # but the type discipline is structural, not procedural).
        typed = ToolCallPayload.model_validate(payload_dict)
        result = stub.process_refund(typed)
        log.append(
            kind="refund_api_call",
            correlation_id=verdict.correlation_id,
            payload={
                "status": result["status"],
                "source": result["source"],
                "amount": result["refunded_amount"],
                "currency": result["currency"],
            },
        )
        return verdict, None, result

    structured = build_structured_error(verdict, policy)
    if verdict.reason_code in ESCALATING_REASON_CODES:
        # On hook_failure the payload may be malformed — pass digest=None
        # so build_escalation_event uses the all-zero sentinel; on
        # policy_breach the payload validates by definition (it passed step 1
        # of the hook), so we recompute the digest from the typed shape.
        if verdict.reason_code == ReasonCode.POLICY_BREACH and policy is not None:
            typed_payload = ToolCallPayload.model_validate(payload_dict)
            digest = compute_payload_digest(typed_payload)
            event = build_escalation_event(
                verdict=verdict,
                policy=policy,
                payload=typed_payload,
                payload_digest=digest,
                reason="policy_breach",
            )
        else:
            event = build_escalation_event(
                verdict=verdict,
                policy=None,
                payload=None,
                payload_digest=None,
                reason="hook_failure",
            )
        emit_escalation(log, event)
    return verdict, structured, None


def _build_parser() -> argparse.ArgumentParser:
    """Argparse wiring for ``python -m katas.kata_002_pretool_guardrails.runner``."""
    parser = argparse.ArgumentParser(
        prog="kata_002_pretool_guardrails",
        description=(
            "Run a single PreToolUse refund invocation against the seeded policy. "
            "Reads payload JSON from --payload (file path) or stdin."
        ),
    )
    parser.add_argument(
        "--payload",
        type=Path,
        help="Path to a ToolCallPayload JSON fixture. If omitted, reads stdin.",
    )
    parser.add_argument(
        "--policy",
        type=Path,
        default=DEFAULT_POLICY_PATH,
        help="Path to the policy JSON file (default: config/policy.json).",
    )
    parser.add_argument(
        "--session-dir",
        type=Path,
        default=None,
        help="Per-session run directory; defaults to runs/<uuid>/.",
    )
    return parser


def _read_payload(path: Path | None) -> dict[str, Any]:
    """Load the payload JSON from path or stdin."""
    if path is None:
        raw = sys.stdin.read()
    else:
        raw = path.read_text(encoding="utf-8")
    return json.loads(raw)


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns the exit code (see module docstring)."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    payload = _read_payload(args.payload)
    session_dir = args.session_dir or (Path("runs") / str(uuid.uuid4()))
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=args.policy,
        session_dir=session_dir,
    )
    output: dict[str, Any] = {
        "session_dir": str(session_dir),
        "verdict": verdict.model_dump(mode="json"),
    }
    if structured is not None:
        output["structured_error"] = structured.model_dump(mode="json")
    if success is not None:
        output["success"] = success
    sys.stdout.write(json.dumps(output, sort_keys=True, indent=2) + "\n")
    return _exit_code_for(verdict)


if __name__ == "__main__":  # pragma: no cover — CLI shim
    raise SystemExit(main())
