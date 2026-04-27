"""Append-only JSONL event-log writer.

Why this module exists:
    Constitution Principle VII (Provenance & Self-Audit) requires that every
    kata run be reconstructible offline from a durable artefact. This writer
    is that artefact: one ``EventRecord`` per loop iteration, serialized in a
    stable shape, fsynced on close. SC-008 says "the log alone is enough to
    reconstruct the trajectory" — so this file is allowed to record the
    structural signal (`stop_signal`, `branch_taken`, `tool_outcome`,
    `termination_cause`) and explicitly NOT permitted to record any
    text-derived field. The strict ``EventRecord`` model enforces that.

The writer also exposes a ``frozen_clock`` mode that the reproducibility
tests (SC-007) flip on so two runs against the same fixture produce
byte-identical files.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import EventRecord

# The frozen clock used by SC-007 tests — when set, every emitted record
# stamps with this value instead of "now". Off in production paths.
_FROZEN_CLOCK: datetime | None = None


def set_frozen_clock(when: datetime | None) -> None:
    """Pin (or unpin) the timestamp the next ``emit`` will stamp.

    Why: byte-identical diffs across two runs (SC-007) require eliminating
    the only non-deterministic field on ``EventRecord`` — the timestamp.
    """
    global _FROZEN_CLOCK  # noqa: PLW0603 — module-level test seam, not state
    _FROZEN_CLOCK = when


def _now_utc() -> datetime:
    """Return current UTC time, or the frozen clock when set."""
    if _FROZEN_CLOCK is not None:
        return _FROZEN_CLOCK
    return datetime.now(tz=UTC)


def serialize_record(record: EventRecord) -> str:
    """Serialize one record as a single deterministic JSON line.

    Why deterministic: ``json.dumps`` sorts keys so two runs producing the
    same logical record produce identical bytes. ``ensure_ascii`` matches the
    schema (which assumes plain ASCII) and avoids locale-dependent encoding.
    """
    payload: dict[str, Any] = record.model_dump(mode="json")
    return json.dumps(payload, sort_keys=True, ensure_ascii=True)


class EventLog:
    """Append-only JSONL writer rooted at ``runs/<session_id>/events.jsonl``.

    Lifetime is one session. ``close`` fsyncs so post-crash replay is safe.
    """

    def __init__(
        self,
        runs_root: Path,
        session_id: str,
        *,
        clock: Callable[[], datetime] = _now_utc,
    ) -> None:
        """Open ``runs_root/<session_id>/events.jsonl`` for append."""
        self._dir = runs_root / session_id
        self._dir.mkdir(parents=True, exist_ok=True)
        self._path = self._dir / "events.jsonl"
        # ``a`` so the file is created if missing and resumable if not.
        self._fh = self._path.open("a", encoding="utf-8")
        self._session_id = session_id
        self._clock = clock
        self._closed = False

    @property
    def path(self) -> Path:
        """Filesystem path of the JSONL file."""
        return self._path

    def emit(self, record: EventRecord) -> None:
        """Append one ``EventRecord`` to the log.

        Why pass a model instead of kwargs: pydantic ``extra="forbid"`` makes
        it structurally impossible to slip a text-derived field into the log
        — exactly the regression Principle I tells us to prevent.
        """
        if self._closed:
            raise RuntimeError("EventLog is closed")
        line = serialize_record(record)
        self._fh.write(line + "\n")
        self._fh.flush()

    def stamp(self) -> datetime:
        """Return a timestamp from the configured clock (used by the loop)."""
        return self._clock()

    def close(self) -> None:
        """Flush + fsync the underlying file and close the handle."""
        if self._closed:
            return
        self._fh.flush()
        try:
            os.fsync(self._fh.fileno())
        except OSError:
            # Filesystems that do not support fsync (e.g. some tmp mounts)
            # must not abort the run; the line buffering above is already
            # flushed.
            pass
        self._fh.close()
        self._closed = True

    def __enter__(self) -> EventLog:
        """Context-manager entry — return self so ``with`` binds the writer."""
        return self

    def __exit__(self, *_exc: object) -> None:
        """Context-manager exit — close the underlying file regardless of error."""
        self.close()
