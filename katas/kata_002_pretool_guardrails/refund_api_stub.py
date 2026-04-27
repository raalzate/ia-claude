"""Local stub of the "external" refund API.

Why this module exists:
    SC-002 demands a *machine-checkable* zero-call assertion on reject
    verdicts. The simplest way to make that assertion bulletproof is to
    have the stub log every call it receives to disk; tests then assert
    the log is empty. Mocking the external SDK call would push the check
    into the language runtime (pytest-mock) where a regression in mock
    setup can silently flip the assertion. Filesystem evidence cannot.

Why a "real" success response on allow:
    US1-AS2 says the success outcome must be derived from the API response,
    not synthesized by the hook layer. The stub returns a structured success
    object so the runner can hand the response back to the model verbatim
    (it is the only path that touches the user-facing success message).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import ToolCallPayload

SOURCE = "refund_api_stub"
"""Identifier surfaced to the agent so US1-AS2 tests can verify provenance.

Why constant: the test ``test_within_policy_refund`` asserts the success
outcome carries ``source == "refund_api_stub"``. A non-stubbed real API
would return a different ``source`` (or none at all), so the assertion
falls through if the wiring ever bypasses the stub.
"""


class RefundApiStub:
    """In-process stand-in for the external refund API.

    Why a class: the per-session call log path is state — passing it as a
    constructor argument keeps tests parallel-safe (each test owns its own
    log path) and makes the dependency obvious to readers.
    """

    def __init__(self, log_path: Path) -> None:
        """Pin the call-log location for this session."""
        self._log_path = Path(log_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def log_path(self) -> Path:
        """Absolute path to the ``refund_api_calls.jsonl`` log."""
        return self._log_path

    def process_refund(self, payload: ToolCallPayload) -> dict[str, Any]:
        """Record the call and return a canned success response.

        The whole point of this method is its *side effect on disk*: every
        invocation appends a line to ``refund_api_calls.jsonl``. Tests
        assert the file is empty on reject verdicts (SC-002) and contains
        exactly one line on allow verdicts (US1-AS1).
        """
        record = {
            "tool_name": payload.tool_name,
            "correlation_id": payload.correlation_id,
            "amount": str(payload.amount),
            "currency": payload.currency,
            "customer_id": payload.customer_id,
            "received_at": datetime.now(tz=UTC).isoformat(),
        }
        with self._log_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
        return {
            "status": "success",
            "source": SOURCE,
            "correlation_id": payload.correlation_id,
            "refunded_amount": str(payload.amount),
            "currency": payload.currency,
            "received_at": record["received_at"],
        }
