"""Cover runner.py helpers + edge branches that the BDD suite skips.

Why a separate file:
    The BDD suite drives `run_once` end-to-end on the happy paths and the
    common reject paths. The coverage gap is the runner's small helpers
    (`_exit_code_for`, `build_structured_error` for `schema_violation` and
    `hook_failure`, `main()` CLI), plus a couple of EventLog/policy edge
    branches that don't fire under normal fixture inputs. Those branches
    are part of the contract — covering them deterministically here keeps
    the coverage gate honest.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from katas.kata_002_pretool_guardrails.errors import ReasonCode
from katas.kata_002_pretool_guardrails.events import EventLog
from katas.kata_002_pretool_guardrails.models import HookVerdict, PolicyConfig, ToolCallPayload
from katas.kata_002_pretool_guardrails.policy import PolicyLoadError, load_policy
from katas.kata_002_pretool_guardrails.refund_api_stub import RefundApiStub
from katas.kata_002_pretool_guardrails.runner import (
    EXIT_ALLOW,
    EXIT_HOOK_FAILURE,
    EXIT_POLICY_BREACH,
    EXIT_SCHEMA_VIOLATION,
    _exit_code_for,
    build_structured_error,
    main,
)

from ..conftest import FIXTURES_DIR


def _verdict(verdict_value: str, reason: ReasonCode | None) -> HookVerdict:
    return HookVerdict(
        verdict=verdict_value,  # type: ignore[arg-type]
        reason_code=reason,
        correlation_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        policy_id="refund-policy",
        policy_snapshot_version="v1",
        evaluated_at=datetime(2026, 4, 27, tzinfo=UTC),
        offending_field=None if verdict_value == "allow" else "amount",
        offending_value=None,
    )


def _policy() -> PolicyConfig:
    return PolicyConfig(
        policy_id="refund-policy",
        policy_snapshot_version="v1",
        max_refund=Decimal("500.00"),
        comparison_stance="strict_less_than",
        escalation_pathway="refund-review-queue",
        effective_from=datetime(2026, 4, 23, tzinfo=UTC),
    )


def test_exit_code_mapping_covers_every_reason() -> None:
    """Every (verdict, reason_code) pair maps to exactly one exit code."""
    assert _exit_code_for(_verdict("allow", None)) == EXIT_ALLOW
    assert _exit_code_for(_verdict("reject", ReasonCode.SCHEMA_VIOLATION)) == EXIT_SCHEMA_VIOLATION
    assert _exit_code_for(_verdict("reject", ReasonCode.POLICY_BREACH)) == EXIT_POLICY_BREACH
    assert _exit_code_for(_verdict("reject", ReasonCode.HOOK_FAILURE)) == EXIT_HOOK_FAILURE


def test_build_structured_error_for_schema_violation_returns_client_fix_required() -> None:
    """schema_violation rejects route to ``client_fix_required`` (D-007)."""
    verdict = _verdict("reject", ReasonCode.SCHEMA_VIOLATION)
    se = build_structured_error(verdict, _policy())
    assert se.reason_code == ReasonCode.SCHEMA_VIOLATION
    assert se.escalation_pathway == "client_fix_required"
    assert se.policy_id is None
    assert se.policy_snapshot_version is None


def test_build_structured_error_for_hook_failure_routes_to_oncall() -> None:
    """hook_failure rejects route to ``hook-failure-oncall``."""
    verdict = _verdict("reject", ReasonCode.HOOK_FAILURE)
    se = build_structured_error(verdict, None)
    assert se.reason_code == ReasonCode.HOOK_FAILURE
    assert se.escalation_pathway == "hook-failure-oncall"


def test_build_structured_error_rejects_allow_input() -> None:
    """build_structured_error MUST refuse to build a non-error from an allow."""
    with pytest.raises(ValueError):
        build_structured_error(_verdict("allow", None), _policy())


def test_main_cli_round_trip_exits_zero_on_allow(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``main()`` reads the payload from --payload and exits 0 on allow."""
    payload_path = FIXTURES_DIR / "within_limit.json"
    rc = main(
        [
            "--payload",
            str(payload_path),
            "--policy",
            str(policy_snapshotter),
            "--session-dir",
            str(session_tmpdir / "main_run"),
        ]
    )
    assert rc == EXIT_ALLOW
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["verdict"]["verdict"] == "allow"


def test_main_cli_reads_stdin_when_payload_omitted(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """If --payload is omitted, main() reads JSON from stdin."""
    import io

    payload = (FIXTURES_DIR / "within_limit.json").read_text()
    monkeypatch.setattr(sys, "stdin", io.StringIO(payload))
    rc = main(
        [
            "--policy",
            str(policy_snapshotter),
            "--session-dir",
            str(session_tmpdir / "stdin_run"),
        ]
    )
    assert rc == EXIT_ALLOW


def test_event_log_serializes_basemodel(session_tmpdir: Path) -> None:
    """EventLog serializes pydantic models via the BaseModel branch."""
    log = EventLog(session_tmpdir)
    payload = ToolCallPayload(
        tool_name="process_refund",
        correlation_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        amount=Decimal("100.00"),
        currency="USD",
        customer_id="C-bbb",
    )
    log.append(kind="invocation", correlation_id=payload.correlation_id, payload=payload)
    written = log.events_path.read_text()
    record = json.loads(written.splitlines()[0])
    assert record["payload"]["tool_name"] == "process_refund"


def test_event_log_serializes_decimal_and_datetime(session_tmpdir: Path) -> None:
    """The custom JSON default handles Decimal and datetime values."""
    log = EventLog(session_tmpdir)
    log.append(
        kind="other",
        correlation_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        payload={"amount": Decimal("12.34"), "when": datetime(2026, 4, 27, tzinfo=UTC)},
    )
    record = json.loads(log.events_path.read_text().splitlines()[0])
    assert record["payload"]["amount"] == "12.34"
    assert record["payload"]["when"].startswith("2026-04-27")


def test_event_log_raises_on_non_serializable(session_tmpdir: Path) -> None:
    """Non-serializable values raise TypeError at serialization."""
    log = EventLog(session_tmpdir)
    with pytest.raises(TypeError):
        log.append(
            kind="other",
            correlation_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            payload={"unsupported": object()},
        )


def test_refund_api_stub_records_success_response(session_tmpdir: Path) -> None:
    """RefundApiStub returns a structured success body and logs the call."""
    stub = RefundApiStub(log_path=session_tmpdir / "calls.jsonl")
    payload = ToolCallPayload(
        tool_name="process_refund",
        correlation_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
        amount=Decimal("50.00"),
        currency="USD",
        customer_id="C-eee",
    )
    response = stub.process_refund(payload)
    assert response["status"] == "success"
    assert response["source"] == "refund_api_stub"
    line = (session_tmpdir / "calls.jsonl").read_text().splitlines()[0]
    assert json.loads(line)["correlation_id"] == payload.correlation_id


def test_load_policy_raises_on_missing_file(tmp_path: Path) -> None:
    """``load_policy`` translates a missing file into ``PolicyLoadError``."""
    with pytest.raises(PolicyLoadError):
        load_policy(tmp_path / "absent.json")


def test_load_policy_raises_on_non_object_root(tmp_path: Path) -> None:
    """Root must be a JSON object, not an array or scalar."""
    target = tmp_path / "policy.json"
    target.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(PolicyLoadError):
        load_policy(target)
