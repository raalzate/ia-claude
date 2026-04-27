"""pytest-bdd step definitions for ``within_policy_refund.feature``.

Why this file: TS-001 / TS-002 acceptance scenarios are owned by the locked
``.feature`` file under ``specs/002-pretool-guardrails/tests/features/``.
Step bindings translate Gherkin clauses into application calls; the
``.feature`` file MUST NOT be edited (see assertion-integrity rules).
"""

from __future__ import annotations

import json
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FEATURES_DIR, FIXTURES_DIR

scenarios(str(FEATURES_DIR / "within_policy_refund.feature"))


# ---------------------------------------------------------------------------
# Givens — set up fixtures, policy snapshot, and payload context
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a configured refund policy with a positive max_refund limit"),
)
def _given_policy_positive(policy_snapshotter: Path) -> None:
    """Use the snapshotted seed policy (max_refund=500.00 USD)."""


@given(
    parsers.parse("a schema-valid refund payload whose amount is strictly below the policy limit"),
    target_fixture="payload",
)
def _given_payload_within_limit() -> dict:
    """Load ``within_limit.json`` (amount=120.00 < 500.00)."""
    return json.loads((FIXTURES_DIR / "within_limit.json").read_text())


@given(parsers.parse("a schema-valid in-policy refund request"), target_fixture="payload")
def _given_payload_in_policy(policy_snapshotter: Path) -> dict:
    """Load the within-limit payload AND ensure the policy snapshot is in place.

    Why ``policy_snapshotter`` here too: TS-002 omits the explicit "configured
    refund policy" Given but still depends on the snapshot being copied. By
    requesting the fixture from this step we guarantee a clean snapshot under
    the per-test tmpdir without needing a separate Given clause.
    """
    return json.loads((FIXTURES_DIR / "within_limit.json").read_text())


@given(parsers.parse("the external refund API stub is configured to respond successfully"))
def _given_stub_configured() -> None:
    """The stub always responds successfully; this is a no-op assertion of intent."""


# ---------------------------------------------------------------------------
# Whens — drive the runner
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
    parsers.parse("the PreToolUse hook allows the invocation and the stub responds"),
    target_fixture="run_result",
)
def _when_allow_and_stub(
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
# Thens — assert against the verdict, the stub log, and the audit log
# ---------------------------------------------------------------------------


@then(parsers.parse('the hook emits a verdict with value "{value}"'))
def _then_verdict_value(run_result: dict, value: str) -> None:
    assert run_result["verdict"].verdict == value


@then(
    parsers.parse(
        "the external refund API receives exactly one call with the original payload"
    )
)
def _then_one_api_call(run_result: dict, read_jsonl, payload: dict) -> None:
    log = read_jsonl(run_result["session_dir"] / "refund_api_calls.jsonl")
    assert len(log) == 1
    assert log[0]["correlation_id"] == payload["correlation_id"]
    assert log[0]["amount"] == payload["amount"]
    assert log[0]["currency"] == payload["currency"]
    assert log[0]["customer_id"] == payload["customer_id"]


@then(
    parsers.parse(
        "the audit log records exactly one refund_api_call entry for the correlation_id"
    )
)
def _then_audit_one_refund_api_call(run_result: dict, read_jsonl, payload: dict) -> None:
    events = read_jsonl(run_result["session_dir"] / "events.jsonl")
    refund_calls = [
        e
        for e in events
        if e["kind"] == "refund_api_call" and e["correlation_id"] == payload["correlation_id"]
    ]
    assert len(refund_calls) == 1


@then(
    parsers.parse(
        "the agent surfaces a success outcome derived from the real API response"
    )
)
def _then_success_from_real_api(run_result: dict) -> None:
    assert run_result["success"] is not None
    assert run_result["success"]["status"] == "success"
    assert run_result["success"]["source"] == "refund_api_stub"


@then(parsers.parse("the success outcome is not synthesized by the hook layer"))
def _then_not_synthesized(run_result: dict) -> None:
    # The hook layer never returns a success body — only the runner does, after
    # the stub responds. ``success`` would be ``None`` if the hook had
    # rejected; the absence of the hook synthesizing a success is structural,
    # not asserted via prose.
    assert run_result["success"] is not None
    assert "source" in run_result["success"]
    assert run_result["success"]["source"] == "refund_api_stub"
