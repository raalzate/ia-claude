"""pytest-bdd step definitions for ``over_limit_blocking.feature``.

Why this binds the WHOLE file (``scenarios()``):
    Every scenario in ``over_limit_blocking.feature`` shares the same
    Background ("a configured refund policy with limit L" + "a schema-valid
    payload whose amount > L"). Binding the whole file in one module keeps
    the Background steps DRY across the five scenarios.
"""

from __future__ import annotations

import json
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FEATURES_DIR, FIXTURES_DIR

scenarios(str(FEATURES_DIR / "over_limit_blocking.feature"))


# ---------------------------------------------------------------------------
# Background — policy + over-limit payload
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a configured refund policy with limit L"),
)
def _given_policy_with_limit(policy_snapshotter: Path) -> None:
    """Use the snapshot's max_refund=500.00 (the seeded L)."""


@given(
    parsers.parse("a schema-valid refund payload whose amount is strictly greater than L"),
    target_fixture="payload",
)
def _given_payload_over_limit() -> dict:
    return json.loads((FIXTURES_DIR / "over_limit.json").read_text())


@given(
    parsers.parse("a system prompt that does not mention any dollar limit"),
)
def _given_clean_prompt() -> None:
    """The prompt module is asserted clean by ``test_prompt_has_no_limit``.

    Why a no-op here: the AST lint already enforces the absence of any
    numeric limit in the prompt. Re-running that check inside a Gherkin
    step would duplicate the mechanism; this clause exists only to make
    the scenario read naturally to a human reviewer.
    """


# ---------------------------------------------------------------------------
# When — drive the runner
# ---------------------------------------------------------------------------


@when(
    parsers.parse("the PreToolUse hook evaluates the refund invocation"),
    target_fixture="run_result",
)
def _when_evaluate(
    payload: dict, policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    return {
        "verdict": verdict,
        "structured": structured,
        "success": success,
        "session_dir": session_tmpdir,
    }


@when(
    parsers.parse("the PreToolUse hook rejects the over-limit invocation"),
    target_fixture="run_result",
)
def _when_evaluate_alias(
    payload: dict, policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    return {
        "verdict": verdict,
        "structured": structured,
        "success": success,
        "session_dir": session_tmpdir,
    }


@when(
    parsers.parse(
        "the PreToolUse hook evaluates the over-limit invocation twice "
        "with the same policy snapshot"
    ),
    target_fixture="run_result",
)
def _when_evaluate_twice(
    payload: dict, policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    first = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir / "first",
    )
    second = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir / "second",
    )
    return {"first": first, "second": second}


@when(
    parsers.parse("the PreToolUse hook evaluates the over-limit invocation"),
    target_fixture="run_result",
)
def _when_evaluate_over_limit(
    payload: dict, policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    return {
        "verdict": verdict,
        "structured": structured,
        "success": success,
        "session_dir": session_tmpdir,
    }


# ---------------------------------------------------------------------------
# Thens
# ---------------------------------------------------------------------------


@then(parsers.parse('the hook emits a verdict with value "{value}"'))
def _then_verdict_value(run_result: dict, value: str) -> None:
    verdict = run_result.get("verdict") or run_result["first"][0]
    assert verdict.verdict == value


@then(parsers.parse('the verdict reason_code is "{value}"'))
def _then_reason_code(run_result: dict, value: str) -> None:
    verdict = run_result.get("verdict") or run_result["first"][0]
    assert verdict.reason_code is not None
    assert verdict.reason_code.value == value


@then(parsers.parse("zero refund API calls are observed for the invocation correlation_id"))
def _then_zero_calls(run_result: dict, read_jsonl) -> None:
    log_path = run_result["session_dir"] / "refund_api_calls.jsonl"
    assert read_jsonl(log_path) == []


@then(parsers.parse("the model's next context window receives a StructuredError object"))
def _then_structured_present(run_result: dict) -> None:
    assert run_result["structured"] is not None


@then(parsers.parse('the StructuredError carries reason_code "{value}"'))
def _then_structured_reason(run_result: dict, value: str) -> None:
    assert run_result["structured"].reason_code.value == value


@then(parsers.parse('the StructuredError identifies the offending field as "{field}"'))
def _then_structured_field(run_result: dict, field: str) -> None:
    assert run_result["structured"].field == field


@then(parsers.parse("the StructuredError cites the policy_id and policy_snapshot_version that was breached"))
def _then_structured_policy(run_result: dict) -> None:
    se = run_result["structured"]
    assert se.policy_id == "refund-policy"
    assert se.policy_snapshot_version == "v1"


@then(parsers.parse("the StructuredError carries a non-empty escalation_pathway"))
def _then_pathway(run_result: dict) -> None:
    assert run_result["structured"].escalation_pathway


@then(parsers.parse("no free-text apology is returned via the tool channel"))
def _then_no_free_text(run_result: dict) -> None:
    # The tool channel returns a typed StructuredError or a typed success
    # body — never a free-form string. Asserting the only API the runner
    # exposes is structured is the structural guarantee.
    assert run_result["structured"] is not None
    assert isinstance(
        run_result["structured"].model_dump(mode="json"), dict
    )


@then(parsers.parse("an EscalationEvent is appended to the audit log"))
def _then_escalation_present(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert len(escalations) == 1


@then(parsers.parse('the EscalationEvent has escalation_reason "{value}"'))
def _then_escalation_reason(run_result: dict, read_jsonl, value: str) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert escalations[0]["payload"]["escalation_reason"] == value


@then(parsers.parse("the EscalationEvent actions_taken list is empty"))
def _then_actions_empty(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert escalations[0]["payload"]["actions_taken"] == []


@then(parsers.parse("the EscalationEvent routing_target equals the policy escalation_pathway"))
def _then_routing(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert escalations[0]["payload"]["routing_target"] == "refund-review-queue"


@then(parsers.parse("the EscalationEvent references the same correlation_id as the verdict"))
def _then_escalation_cid(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert escalations[0]["correlation_id"] == run_result["verdict"].correlation_id


@then(parsers.parse("both verdicts are equal in every field except evaluated_at"))
def _then_byte_equal_verdicts(run_result: dict) -> None:
    first = run_result["first"][0].model_dump(mode="json")
    second = run_result["second"][0].model_dump(mode="json")
    first.pop("evaluated_at")
    second.pop("evaluated_at")
    assert first == second


@then(parsers.parse('both verdicts carry reason_code "{value}"'))
def _then_both_reason(run_result: dict, value: str) -> None:
    assert run_result["first"][0].reason_code.value == value
    assert run_result["second"][0].reason_code.value == value


@then(parsers.parse("no numeric literal matching the policy max_refund appears in the system prompt module"))
def _then_no_literal_in_prompt() -> None:
    """Re-assert FR-008 via the same AST lint mechanism.

    Why duplicate the lint test's logic here: the Gherkin scenario must be
    self-checking; pulling in the production AST scan keeps the assertion
    one source-of-truth — the lint test and the BDD step share the same
    helper module so a regression in one fails both.
    """
    from tests.katas.kata_002_pretool_guardrails.lint.test_prompt_has_no_limit import (
        test_prompts_module_contains_no_max_refund_literal,
    )

    test_prompts_module_contains_no_max_refund_literal()


@then(parsers.parse("the audit log contains a verdict record with the invocation correlation_id"))
def _then_audit_verdict(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    verdicts = [
        e
        for e in events
        if e["kind"] == "verdict"
        and e["correlation_id"] == run_result["verdict"].correlation_id
    ]
    assert len(verdicts) == 1


@then(parsers.parse("the record carries a timestamp, policy_id, policy_snapshot_version, offending_field, and offending_value"))
def _then_audit_record_fields(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    verdicts = [e for e in events if e["kind"] == "verdict"]
    payload = verdicts[0]["payload"]
    for field in (
        "evaluated_at",
        "policy_id",
        "policy_snapshot_version",
        "offending_field",
        "offending_value",
    ):
        assert field in payload, f"missing field: {field}"


@then(parsers.parse("the record ties to both the StructuredError and the EscalationEvent via the correlation_id"))
def _then_record_ties(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    verdicts = [e for e in events if e["kind"] == "verdict"]
    escalations = [e for e in events if e["kind"] == "escalation"]
    cid = verdicts[0]["correlation_id"]
    assert escalations[0]["correlation_id"] == cid
    assert run_result["structured"].correlation_id == cid
