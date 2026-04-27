"""TS-012: payload with extra unknown fields → schema_violation (extra="forbid")."""

from __future__ import annotations

import json
from pathlib import Path

from katas.kata_002_pretool_guardrails.runner import run_once

from ..conftest import FIXTURES_DIR


def test_extra_fields_rejects_as_schema_violation(
    policy_snapshotter: Path,
    session_tmpdir: Path,
    read_jsonl,
) -> None:
    payload = json.loads((FIXTURES_DIR / "extra_fields.json").read_text())
    verdict, _structured, _success = run_once(
        payload_dict=payload,
        policy_path=policy_snapshotter,
        session_dir=session_tmpdir,
    )
    assert verdict.verdict == "reject"
    assert verdict.reason_code is not None
    assert verdict.reason_code.value == "schema_violation"
    assert read_jsonl(session_tmpdir / "refund_api_calls.jsonl") == []
