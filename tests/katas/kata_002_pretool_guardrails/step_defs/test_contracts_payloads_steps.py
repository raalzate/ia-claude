"""Step defs for contract-validation scenarios in ``contracts.feature``.

Why split across files:
    TS-021 (directory listing) and TS-019 (PolicyConfig) belong with their
    respective concerns and are bound elsewhere. The five scenarios below
    (TS-016, TS-017, TS-018, TS-020, TS-022) all validate one
    boundary-crossing object against its JSON Schema, so they share one
    file and a tight set of helpers.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal

import jsonschema
import pytest
from pydantic import ValidationError
from pytest_bdd import given, parsers, scenario, then, when

from katas.kata_002_pretool_guardrails.escalation import (
    build_escalation_event,
    compute_payload_digest,
)
from katas.kata_002_pretool_guardrails.hook import RefundPolicyHook
from katas.kata_002_pretool_guardrails.models import (
    EscalationEvent,
    PolicyConfig,
    StructuredError,
    ToolCallPayload,
)
from katas.kata_002_pretool_guardrails.runner import build_structured_error

from ..conftest import REPO_ROOT

CONTRACTS_DIR = REPO_ROOT / "specs" / "002-pretool-guardrails" / "contracts"
FEATURE_FILE = REPO_ROOT / "specs" / "002-pretool-guardrails" / "tests" / "features" / "contracts.feature"


def _load_schema(filename: str) -> dict:
    return json.loads((CONTRACTS_DIR / filename).read_text())


def _seed_policy(version: str = "v1", limit: str = "500.00") -> PolicyConfig:
    return PolicyConfig(
        policy_id="refund-policy",
        policy_snapshot_version=version,
        max_refund=Decimal(limit),
        comparison_stance="strict_less_than",
        escalation_pathway="refund-review-queue",
        effective_from=datetime(2026, 4, 23, tzinfo=UTC),
    )


def _seed_payload(amount: str = "120.00") -> ToolCallPayload:
    return ToolCallPayload(
        tool_name="process_refund",
        correlation_id="11111111-1111-4111-8111-111111111111",
        amount=Decimal(amount),
        currency="USD",
        customer_id="C-1001",
        reason="contracts test",
    )


# ---------------------------------------------------------------------------
# TS-016 — ToolCallPayload validates
# ---------------------------------------------------------------------------


@scenario(str(FEATURE_FILE), "ToolCallPayload instances validate against the tool-call-payload schema")
def test_ts_016_tool_call_payload_validates() -> None:
    """Bind only TS-016 here."""


@given(parsers.parse("a ToolCallPayload object produced by the agent"), target_fixture="payload_object")
def _given_payload_object() -> ToolCallPayload:
    return _seed_payload()


@when(
    parsers.parse("the object is validated against contracts/tool-call-payload.schema.json"),
    target_fixture="schema_validation_result",
)
def _when_validate_payload(payload_object: ToolCallPayload) -> dict:
    schema = _load_schema("tool-call-payload.schema.json")
    serialized = payload_object.model_dump(mode="json")
    serialized["amount"] = str(payload_object.amount)  # decimal-safe string
    jsonschema.Draft202012Validator(schema).validate(serialized)
    return {"object": serialized, "kind": "tool_call_payload"}


@then(parsers.parse("the object passes schema validation"))
def _then_passes_validation(schema_validation_result: dict) -> None:
    assert schema_validation_result["object"]


@then(parsers.parse('the tool_name equals "{value}"'))
def _then_tool_name(schema_validation_result: dict, value: str) -> None:
    assert schema_validation_result["object"]["tool_name"] == value


@then(parsers.parse('the currency equals "{value}"'))
def _then_currency(schema_validation_result: dict, value: str) -> None:
    assert schema_validation_result["object"]["currency"] == value


# ---------------------------------------------------------------------------
# TS-017 — HookVerdict validates
# ---------------------------------------------------------------------------


@scenario(str(FEATURE_FILE), "HookVerdict instances validate against the hook-verdict schema")
def test_ts_017_hook_verdict_validates() -> None:
    """Bind TS-017."""


@given(parsers.parse("a HookVerdict emitted by the PreToolUseHook"), target_fixture="verdict_pair")
def _given_verdicts() -> dict:
    """Build one allow and one reject verdict so both branches are covered."""
    hook = RefundPolicyHook()
    policy = _seed_policy()
    allow = hook.evaluate(_seed_payload("100.00"), policy)
    reject = hook.evaluate(_seed_payload("700.00"), policy)
    return {"allow": allow, "reject": reject}


@when(
    parsers.parse("the object is validated against contracts/hook-verdict.schema.json"),
    target_fixture="schema_validation_result",
)
def _when_validate_verdicts(verdict_pair: dict) -> dict:
    schema = _load_schema("hook-verdict.schema.json")
    validator = jsonschema.Draft202012Validator(schema)
    allow_dump = verdict_pair["allow"].model_dump(mode="json")
    reject_dump = verdict_pair["reject"].model_dump(mode="json")
    validator.validate(allow_dump)
    validator.validate(reject_dump)
    # Set "object" so the shared _then_passes_validation step sees a value;
    # both verdicts already validated above, so picking one is harmless.
    return {"allow": allow_dump, "reject": reject_dump, "object": reject_dump, "kind": "hook_verdict"}


@then(parsers.parse("on reject the reason_code and offending_field are non-null"))
def _then_reject_fields(schema_validation_result: dict) -> None:
    reject = schema_validation_result["reject"]
    assert reject["reason_code"] is not None
    assert reject["offending_field"] is not None


@then(parsers.parse("on allow the reason_code and offending_field are null"))
def _then_allow_fields(schema_validation_result: dict) -> None:
    allow = schema_validation_result["allow"]
    assert allow["reason_code"] is None
    assert allow["offending_field"] is None


# ---------------------------------------------------------------------------
# TS-018 — StructuredError validates
# ---------------------------------------------------------------------------


@scenario(str(FEATURE_FILE), "StructuredError instances validate against the structured-error schema")
def test_ts_018_structured_error_validates() -> None:
    """Bind TS-018."""


@given(
    parsers.parse("a StructuredError returned into the model context on a reject verdict"),
    target_fixture="structured_object",
)
def _given_structured() -> StructuredError:
    hook = RefundPolicyHook()
    policy = _seed_policy()
    verdict = hook.evaluate(_seed_payload("700.00"), policy)
    return build_structured_error(verdict, policy)


@when(
    parsers.parse("the object is validated against contracts/structured-error.schema.json"),
    target_fixture="schema_validation_result",
)
def _when_validate_structured(structured_object: StructuredError) -> dict:
    schema = _load_schema("structured-error.schema.json")
    serialized = structured_object.model_dump(mode="json")
    jsonschema.Draft202012Validator(schema).validate(serialized)
    return {"object": serialized, "kind": "structured_error"}


@then(parsers.parse('the verdict equals "{value}"'))
def _then_verdict_equals(schema_validation_result: dict, value: str) -> None:
    assert schema_validation_result["object"]["verdict"] == value


@then(parsers.parse('on reason_code "policy_breach" the policy_id and policy_snapshot_version are non-null'))
def _then_breach_policy_fields(schema_validation_result: dict) -> None:
    obj = schema_validation_result["object"]
    if obj["reason_code"] == "policy_breach":
        assert obj["policy_id"] is not None
        assert obj["policy_snapshot_version"] is not None


@then(parsers.parse('on reason_code "schema_violation" or "hook_failure" the policy_id and policy_snapshot_version are null'))
def _then_other_policy_fields_null(schema_validation_result: dict) -> None:
    obj = schema_validation_result["object"]
    if obj["reason_code"] in ("schema_violation", "hook_failure"):
        assert obj["policy_id"] is None
        assert obj["policy_snapshot_version"] is None


# ---------------------------------------------------------------------------
# TS-020 — EscalationEvent validates
# ---------------------------------------------------------------------------


@scenario(str(FEATURE_FILE), "EscalationEvent instances validate against the escalation-event schema")
def test_ts_020_escalation_event_validates() -> None:
    """Bind TS-020."""


@given(
    parsers.parse(
        "an EscalationEvent written to the audit log on a policy_breach or hook_failure reject"
    ),
    target_fixture="escalation_object",
)
def _given_escalation() -> EscalationEvent:
    hook = RefundPolicyHook()
    policy = _seed_policy()
    payload = _seed_payload("700.00")
    verdict = hook.evaluate(payload, policy)
    return build_escalation_event(
        verdict=verdict,
        policy=policy,
        payload=payload,
        payload_digest=compute_payload_digest(payload),
        reason="policy_breach",
    )


@when(
    parsers.parse("the object is validated against contracts/escalation-event.schema.json"),
    target_fixture="schema_validation_result",
)
def _when_validate_escalation(escalation_object: EscalationEvent) -> dict:
    schema = _load_schema("escalation-event.schema.json")
    serialized = escalation_object.model_dump(mode="json")
    jsonschema.Draft202012Validator(schema).validate(serialized)
    return {"object": serialized, "kind": "escalation"}


@then(parsers.parse('the kind equals "{value}"'))
def _then_kind_equals(schema_validation_result: dict, value: str) -> None:
    assert schema_validation_result["object"]["kind"] == value


@then(parsers.parse("the actions_taken list is empty"))
def _then_actions_empty(schema_validation_result: dict) -> None:
    assert schema_validation_result["object"]["actions_taken"] == []


@then(parsers.parse("the rejected_payload_digest is a 64-character lowercase hex SHA-256"))
def _then_digest_shape(schema_validation_result: dict) -> None:
    digest = schema_validation_result["object"]["rejected_payload_digest"]
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


# ---------------------------------------------------------------------------
# TS-022 — ToolCallPayload rejects non-positive amounts via the data-model invariant
# ---------------------------------------------------------------------------


@scenario(str(FEATURE_FILE), "ToolCallPayload rejects non-positive amounts via the data-model invariant")
def test_ts_022_tool_call_payload_invariant() -> None:
    """Bind TS-022."""


@given(
    parsers.parse("a ToolCallPayload candidate with amount less than or equal to zero"),
    target_fixture="bad_candidate",
)
def _given_nonpositive_candidate() -> dict:
    return {
        "tool_name": "process_refund",
        "correlation_id": "ffffffff-ffff-4fff-8fff-ffffffffffff",
        "amount": Decimal("0"),
        "currency": "USD",
        "customer_id": "C-NEG",
        "reason": "non-positive amount",
    }


@when(
    parsers.parse("the pydantic validator runs"),
    target_fixture="construction_attempt",
)
def _when_construct(bad_candidate: dict) -> dict:
    """Try to construct; capture any ValidationError."""
    try:
        ToolCallPayload.model_validate(bad_candidate)
    except ValidationError as exc:
        return {"raised": True, "exc": exc}
    return {"raised": False, "exc": None}


@then(parsers.parse("construction fails with a ValidationError on the amount field"))
def _then_validation_error_on_amount(construction_attempt: dict) -> None:
    assert construction_attempt["raised"], "construction unexpectedly succeeded"
    locs = [".".join(str(p) for p in err["loc"]) for err in construction_attempt["exc"].errors()]
    assert any("amount" in loc for loc in locs), f"expected error on amount; got {locs}"


# Sanity: pytest.fixture imports above keep the linter happy.
_ = pytest
