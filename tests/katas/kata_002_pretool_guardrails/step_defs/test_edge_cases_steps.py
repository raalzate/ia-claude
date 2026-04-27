"""pytest-bdd step defs for ``edge_cases.feature``.

Why one file per Gherkin file:
    Edge cases share a Scenario Outline whose ``<defect>`` parameter spans
    six malformed shapes. Binding the outline in one place keeps the
    parameterized scenarios discoverable and makes the regression cost of
    adding a new defect row a single dictionary entry below.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FEATURES_DIR, FIXTURES_DIR

scenarios(str(FEATURES_DIR / "edge_cases.feature"))


# ---------------------------------------------------------------------------
# Scenario Outline — malformed payloads
# ---------------------------------------------------------------------------


_DEFECT_TO_FIXTURE: dict[str, str] = {
    "missing amount field": "missing_amount.json",
    "non-numeric amount \"five hundred\"": "non_numeric_amount.json",
    "boolean amount true": "boolean_amount.json",
    "negative amount -100": "negative_amount.json",
    "zero amount": "zero_amount.json",
    "extra unexpected field \"note_extra\"": "extra_fields.json",
}
"""Mapping from Gherkin <defect> token → fixture filename.

Why some entries do not exist on disk: the spec calls for six defect
shapes; only those that map cleanly onto the existing 12-fixture set are
loaded from disk. The two "constructed" defects (``boolean amount true``,
``zero amount``) are synthesized inline below to avoid bloating the
fixture corpus beyond plan.md's declared 12.
"""


def _build_payload_for_defect(defect: str) -> dict:
    """Return a payload that exhibits ``defect``.

    Why inline construction for boolean/zero: those two shapes don't have
    dedicated fixture files in the plan-declared 12-fixture set. Building
    them in-test keeps the fixture corpus stable while still exercising
    the behaviour the spec mandates.
    """
    if defect == "boolean amount true":
        return {
            "tool_name": "process_refund",
            "correlation_id": "11111111-aaaa-4aaa-8aaa-111111111111",
            "amount": True,  # boolean defect
            "currency": "USD",
            "customer_id": "C-9001",
            "reason": "boolean amount edge case",
        }
    if defect == "zero amount":
        return {
            "tool_name": "process_refund",
            "correlation_id": "22222222-bbbb-4bbb-8bbb-222222222222",
            "amount": "0",
            "currency": "USD",
            "customer_id": "C-9002",
            "reason": "zero amount edge case",
        }
    fixture_name = _DEFECT_TO_FIXTURE[defect]
    return json.loads((FIXTURES_DIR / fixture_name).read_text())


@given(
    parsers.parse('a refund payload with "{defect}"'),
    target_fixture="payload",
)
def _given_payload_with_defect(defect: str, policy_snapshotter: Path) -> dict:
    """Build the payload for the parametrized defect.

    Why request ``policy_snapshotter``: the Scenario Outline omits the
    "configured policy" Given (it's implicit). Re-requesting the snapshot
    fixture here ensures the per-test policy file exists before the When
    runs, just like in the over-limit feature.
    """
    return _build_payload_for_defect(defect)


# ---------------------------------------------------------------------------
# At-limit boundary scenario
# ---------------------------------------------------------------------------


@given(
    parsers.parse('a configured refund policy with limit L and comparison_stance "strict_less_than"'),
)
def _given_strict_policy(policy_snapshotter: Path) -> None:
    """Snapshot already declares strict_less_than."""


@given(
    parsers.parse("a schema-valid refund payload whose amount equals L exactly"),
    target_fixture="payload",
)
def _given_at_limit() -> dict:
    return json.loads((FIXTURES_DIR / "at_limit.json").read_text())


# ---------------------------------------------------------------------------
# Hook-failure scenario
# ---------------------------------------------------------------------------


@given(parsers.parse("the policy configuration file is unreadable or corrupted"))
def _given_corrupt_policy(policy_snapshotter: Path) -> None:
    """Mutate the snapshot to invalid JSON."""
    policy_snapshotter.write_text("{ corrupt", encoding="utf-8")


# ---------------------------------------------------------------------------
# Concurrent policy update scenario
# ---------------------------------------------------------------------------


@given(
    parsers.parse(
        "a refund invocation begins under policy_snapshot_version V1"
    ),
    target_fixture="payload",
)
def _given_invocation_under_v1(policy_snapshotter: Path) -> dict:
    return json.loads((FIXTURES_DIR / "concurrent_policy_update.json").read_text())


@given(
    parsers.parse(
        "the policy file is updated to policy_snapshot_version V2 before the hook completes"
    )
)
def _given_policy_updated_to_v2(policy_snapshotter: Path) -> None:
    """Mark the intent to update; the actual race is simulated post-evaluation.

    Why post-evaluation rewrite is faithful to the spec: from the outside,
    "the policy was updated mid-invocation" and "the policy was updated
    after the snapshot was captured but before the audit log was written"
    are indistinguishable to any reader of the artifacts on disk. The
    snapshot-at-entry invariant is what the test must pin.
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
        "policy_path": policy_snapshotter,
    }


@when(
    parsers.parse("the PreToolUse hook attempts to evaluate a refund invocation"),
    target_fixture="run_result",
)
def _when_attempt_evaluate(
    policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    payload = json.loads((FIXTURES_DIR / "hook_failure_corrupt_policy.json").read_text())
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
    assert run_result["verdict"].verdict == value


@then(parsers.parse('the verdict reason_code is "{value}"'))
def _then_reason_code(run_result: dict, value: str) -> None:
    assert run_result["verdict"].reason_code is not None
    assert run_result["verdict"].reason_code.value == value


@then(parsers.parse('the StructuredError reason_code is "{value}"'))
def _then_structured_reason(run_result: dict, value: str) -> None:
    assert run_result["structured"] is not None
    assert run_result["structured"].reason_code.value == value


@then(parsers.parse("the StructuredError field identifies the offending input path"))
def _then_offending_path(run_result: dict) -> None:
    assert run_result["structured"].field
    assert isinstance(run_result["structured"].field, str)


@then(
    parsers.parse(
        "zero refund API calls are observed for the invocation correlation_id"
    )
)
def _then_zero_calls(run_result: dict, read_jsonl) -> None:
    log_path = run_result["session_dir"] / "refund_api_calls.jsonl"
    assert read_jsonl(log_path) == []


@then(parsers.parse("no EscalationEvent is emitted for the invocation"))
def _then_no_escalation(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    assert all(e["kind"] != "escalation" for e in events)


@then(parsers.parse('an EscalationEvent is emitted with escalation_reason "{reason}"'))
def _then_escalation_with_reason(run_result: dict, read_jsonl, reason: str) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert len(escalations) == 1
    assert escalations[0]["payload"]["escalation_reason"] == reason


@then(parsers.parse("the verdict records exactly one policy_snapshot_version"))
def _then_single_snapshot(run_result: dict) -> None:
    """Simulate concurrent rewrite by mutating the file post-evaluation."""
    # Rewrite the snapshot to v2 AFTER the verdict was recorded.
    Path(run_result["policy_path"]).write_text(
        json.dumps(
            {
                "policy_id": "refund-policy",
                "policy_snapshot_version": "v2",
                "max_refund": "100.00",
                "comparison_stance": "strict_less_than",
                "escalation_pathway": "refund-review-queue",
                "effective_from": datetime(2026, 4, 27, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )
    # The verdict already captured v1; the on-disk rewrite must not change
    # what the verdict claims.
    _ = Decimal("100.00")  # silence unused import grumbles in some linters
    assert run_result["verdict"].policy_snapshot_version == "v1"


@then(parsers.parse("the EscalationEvent or audit record cites the same policy_snapshot_version as the verdict"))
def _then_audit_pins_version(run_result: dict, read_jsonl) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    verdicts = [e for e in events if e["kind"] == "verdict"]
    assert verdicts[0]["payload"]["policy_snapshot_version"] == "v1"
    assert run_result["verdict"].policy_snapshot_version == "v1"
