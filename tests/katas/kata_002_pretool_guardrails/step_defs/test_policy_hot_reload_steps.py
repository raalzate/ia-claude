"""pytest-bdd step defs for ``policy_hot_reload.feature``."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from pytest_bdd import given, parsers, scenarios, then, when

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FEATURES_DIR, FIXTURES_DIR

scenarios(str(FEATURES_DIR / "policy_hot_reload.feature"))


def _write_policy(path: Path, version: str, limit: str) -> None:
    path.write_text(
        json.dumps(
            {
                "policy_id": "refund-policy",
                "policy_snapshot_version": version,
                "max_refund": limit,
                "comparison_stance": "strict_less_than",
                "escalation_pathway": "refund-review-queue",
                "effective_from": datetime(2026, 4, 23, tzinfo=UTC).isoformat(),
            }
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Givens
# ---------------------------------------------------------------------------


@given(
    parsers.parse("a policy limit L1 and an amount A with A strictly less than L1"),
    target_fixture="hot_reload_state",
)
def _given_policy_l1_and_amount_a(
    policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    _write_policy(policy_snapshotter, version="L1", limit="500.00")
    payload = json.loads((FIXTURES_DIR / "policy_change_before.json").read_text())
    return {
        "policy_path": policy_snapshotter,
        "session_dir": session_tmpdir,
        "payload": payload,
        "amount": Decimal(payload["amount"]),
        "L1": Decimal("500.00"),
    }


@given(
    parsers.parse("a policy change from L1 to L2 is persisted to the policy configuration"),
    target_fixture="hot_reload_state",
)
def _given_policy_changed(policy_snapshotter: Path, session_tmpdir: Path) -> dict:
    _write_policy(policy_snapshotter, version="L1", limit="500.00")
    _write_policy(policy_snapshotter, version="L2", limit="200.00")
    payload = json.loads((FIXTURES_DIR / "policy_change_after.json").read_text())
    return {
        "policy_path": policy_snapshotter,
        "session_dir": session_tmpdir,
        "payload": payload,
    }


@given(
    parsers.parse("a policy limit L1 is persisted"),
    target_fixture="hot_reload_state",
)
def _given_policy_l1_persisted(
    policy_snapshotter: Path, session_tmpdir: Path
) -> dict:
    _write_policy(policy_snapshotter, version="L1", limit="500.00")
    return {
        "policy_path": policy_snapshotter,
        "session_dir": session_tmpdir,
        "payload": json.loads((FIXTURES_DIR / "policy_change_after.json").read_text()),
    }


# ---------------------------------------------------------------------------
# Whens
# ---------------------------------------------------------------------------


@when(
    parsers.parse("the PreToolUse hook evaluates the refund invocation under limit L1"),
    target_fixture="hot_reload_state",
)
def _when_evaluate_under_l1(hot_reload_state: dict) -> dict:
    verdict, structured, success = run_once(
        payload_dict=hot_reload_state["payload"],
        policy_path=hot_reload_state["policy_path"],
        session_dir=hot_reload_state["session_dir"] / "l1",
    )
    hot_reload_state["last_verdict"] = verdict
    hot_reload_state["last_structured"] = structured
    hot_reload_state["last_success"] = success
    return hot_reload_state


@when(
    parsers.parse(
        "the policy limit is updated from L1 to L2 with L2 strictly less than A strictly less than L1"
    )
)
def _when_lower_to_l2(hot_reload_state: dict) -> None:
    """Lower the limit to a value strictly less than A=300."""
    _write_policy(hot_reload_state["policy_path"], version="L2", limit="200.00")


@when(
    parsers.parse(
        "the PreToolUse hook evaluates the same refund invocation under limit L2"
    ),
    target_fixture="hot_reload_state",
)
def _when_evaluate_under_l2(hot_reload_state: dict) -> dict:
    payload = json.loads((FIXTURES_DIR / "policy_change_after.json").read_text())
    verdict, structured, success = run_once(
        payload_dict=payload,
        policy_path=hot_reload_state["policy_path"],
        session_dir=hot_reload_state["session_dir"] / "l2",
    )
    hot_reload_state["last_verdict"] = verdict
    hot_reload_state["last_structured"] = structured
    hot_reload_state["last_success"] = success
    return hot_reload_state


@when(
    parsers.parse("the next refund invocation is evaluated"),
    target_fixture="hot_reload_state",
)
def _when_next_invocation(hot_reload_state: dict) -> dict:
    verdict, structured, success = run_once(
        payload_dict=hot_reload_state["payload"],
        policy_path=hot_reload_state["policy_path"],
        session_dir=hot_reload_state["session_dir"] / "next",
    )
    hot_reload_state["last_verdict"] = verdict
    hot_reload_state["last_structured"] = structured
    hot_reload_state["last_success"] = success
    return hot_reload_state


@when(parsers.parse("the policy file is updated to limit L2"))
def _when_lower_to_l2_persistence(hot_reload_state: dict) -> None:
    _write_policy(hot_reload_state["policy_path"], version="L2", limit="200.00")


@when(
    parsers.parse("one subsequent refund invocation is evaluated"),
    target_fixture="hot_reload_state",
)
def _when_one_subsequent(hot_reload_state: dict) -> dict:
    verdict, structured, success = run_once(
        payload_dict=hot_reload_state["payload"],
        policy_path=hot_reload_state["policy_path"],
        session_dir=hot_reload_state["session_dir"] / "subsequent",
    )
    hot_reload_state["last_verdict"] = verdict
    hot_reload_state["last_structured"] = structured
    hot_reload_state["last_success"] = success
    return hot_reload_state


# ---------------------------------------------------------------------------
# Thens
# ---------------------------------------------------------------------------


@then(parsers.parse('the hook emits a verdict with value "{value}"'))
def _then_verdict_value(hot_reload_state: dict, value: str) -> None:
    assert hot_reload_state["last_verdict"].verdict == value


@then(parsers.parse('the verdict reason_code is "{value}"'))
def _then_reason_code(hot_reload_state: dict, value: str) -> None:
    assert hot_reload_state["last_verdict"].reason_code is not None
    assert hot_reload_state["last_verdict"].reason_code.value == value


@then(parsers.parse("the StructuredError cites the updated limit L2 and the new policy_snapshot_version"))
def _then_structured_pins_l2(hot_reload_state: dict) -> None:
    structured = hot_reload_state["last_structured"]
    assert structured is not None
    assert structured.policy_snapshot_version == "L2"


@then(parsers.parse("the EscalationEvent references the new policy_snapshot_version"))
def _then_escalation_pins_l2(hot_reload_state: dict, read_jsonl) -> None:
    events_path = hot_reload_state["session_dir"] / "l2" / "events.jsonl"
    events = read_jsonl(events_path)
    escalations = [e for e in events if e["kind"] == "escalation"]
    assert escalations[0]["payload"]["policy_snapshot_version"] == "L2"


@then(parsers.parse("the hook enforces limit L2 without any edit to the system prompt"))
def _then_no_prompt_edit(hot_reload_state: dict) -> None:
    """The AST lint test already proves this; here we re-assert structurally."""
    assert hot_reload_state["last_verdict"].policy_snapshot_version == "L2"


@then(parsers.parse("the hook enforces limit L2 without any edit to the tool schema"))
def _then_no_schema_edit(hot_reload_state: dict) -> None:
    """No contract file is touched by a policy edit (covered by the digest test)."""
    assert hot_reload_state["last_verdict"].policy_snapshot_version == "L2"


@then(parsers.parse("the hook enforces limit L2 without any model redeployment"))
def _then_no_redeploy(hot_reload_state: dict) -> None:
    """No process restart happened in this test (the runner ran in-process)."""
    assert hot_reload_state["last_verdict"].policy_snapshot_version == "L2"


@then(parsers.parse("the verdict is computed against limit L2"))
def _then_against_l2(hot_reload_state: dict) -> None:
    assert hot_reload_state["last_verdict"].policy_snapshot_version == "L2"


@then(parsers.parse("no intermediate invocation observes a stale limit L1"))
def _then_no_stale(hot_reload_state: dict) -> None:
    """Per-invocation reload guarantees this; assert the verdict pinned L2."""
    assert hot_reload_state["last_verdict"].policy_snapshot_version == "L2"
