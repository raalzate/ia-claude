"""Append-only JSONL event-log writer for kata 2.

Why this module exists:
    Constitution Principle VII (Provenance & Self-Audit) and FR-009 require
    every invocation, verdict, escalation, and refund-API call to land on a
    durable artefact, joined by ``correlation_id``, so any session is
    reconstructable offline. The SC-002 zero-call assertion specifically
    relies on the *absence* of ``refund_api_call`` records: if the hook
    rejects, the API stub never fires, no record is written, the
    ``refund_api_calls.jsonl`` file stays empty.

Layout:
    ``runs/<session-id>/events.jsonl`` — every kind of audit record.
    ``runs/<session-id>/refund_api_calls.jsonl`` — only refund_api_call
    mirrors (the stub writes those itself; this module focuses on
    events.jsonl).

Records are tagged by ``kind`` (``invocation`` / ``verdict`` /
``escalation`` / ``refund_api_call``) so a downstream reader can group by
correlation id and recover the full trajectory.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def _serialize_for_json(obj: Any) -> Any:
    """Coerce Decimal/datetime to JSON-friendly types.

    Why: Decimal is the source-of-truth amount type but ``json.dumps``
    cannot serialize it; rendering as a string preserves precision and
    matches the contract schemas which model decimals as strings.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json")
    raise TypeError(f"non-serializable: {type(obj).__name__}")


class EventLog:
    """Append a JSONL line per audit record under a session directory.

    Why instantiate per-session: each test run uses pytest's ``tmp_path``
    so writes from one test cannot leak into another (relevant for SC-002
    bisectability). In production, the session id is the loop run id.
    """

    def __init__(self, session_dir: Path) -> None:
        """Create / locate the session directory and the events file."""
        self._session_dir = Path(session_dir)
        self._session_dir.mkdir(parents=True, exist_ok=True)
        self._events_path = self._session_dir / "events.jsonl"

    @property
    def events_path(self) -> Path:
        """Absolute path to the events JSONL file."""
        return self._events_path

    @property
    def session_dir(self) -> Path:
        """Absolute path to the session directory."""
        return self._session_dir

    def append(self, kind: str, correlation_id: str, payload: Any) -> None:
        """Write one ``{kind, correlation_id, payload, timestamp}`` line.

        Why ``sort_keys=True``: deterministic byte output makes diffs across
        two identical runs cheap (Principle I — determinism shows up in
        the audit log shape too, not only in the verdict).
        """
        record = {
            "kind": kind,
            "correlation_id": correlation_id,
            "timestamp": datetime.now(tz=UTC).isoformat(),
            "payload": payload,
        }
        line = json.dumps(record, sort_keys=True, default=_serialize_for_json)
        with self._events_path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
