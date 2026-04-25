"""Append-only JSONL event-log writer.

Why JSONL and not SQLite/structured logging: research.md D-003. JSONL is the
simplest append-only format that survives crashes and is trivially greppable
(SC-008 — a reviewer reconstructs the trajectory in under five minutes).

Why this writer enforces the EventRecord schema: data-model.md says no
text-derived field is allowed on EventRecord. Pydantic's `extra='forbid'` on
the model rejects unknown keys; this writer additionally serializes with
`exclude_none=False` and stable key ordering so SC-007 (byte-identical
reruns) holds across machines and Python versions.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from katas.kata_001_agentic_loop.models import EventRecord


class EventLog:
    """File-backed JSONL writer, one line per `EventRecord`.

    Why we open the file at construction and close it explicitly: writing
    line-by-line with `os.fsync` on close gives us crash safety without a
    background flush loop. The kata is short-lived; nothing more clever pays
    off here.
    """

    def __init__(self, path: str | Path) -> None:
        """Open `path` in append mode, creating parent directories as needed."""
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Why "a" + line-buffering: append-only is a hard requirement
        # (Principle VII); line-buffering means each `emit` is a complete
        # line on disk before the next call.
        self._fh = self._path.open("a", encoding="utf-8", buffering=1)

    @property
    def path(self) -> Path:
        """Filesystem path of the JSONL log."""
        return self._path

    def emit(self, record: EventRecord) -> None:
        """Append one record as a single JSON line.

        Why `model_dump(mode="json")` then `json.dumps(..., sort_keys=True)`:
        the model handles type coercion (datetime → ISO 8601), then we fix
        key order so two reruns produce identical bytes.
        """
        payload = record.model_dump(mode="json")
        # Why we hand-format the timestamp with microsecond precision: the
        # default ISO-8601 form drops microseconds when zero, making byte
        # diffs noisy. Stable formatting trumps default brevity here.
        if isinstance(record.timestamp, datetime):
            payload["timestamp"] = record.timestamp.astimezone(UTC).isoformat(
                timespec="microseconds"
            )
        line = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        self._fh.write(line + "\n")

    def close(self) -> None:
        """Flush, fsync, and close.

        Why fsync explicitly: the kata may crash mid-run during teaching; a
        truncated event log would leave the practitioner unable to reconstruct
        the trajectory (SC-008).
        """
        try:
            self._fh.flush()
            os.fsync(self._fh.fileno())
        finally:
            self._fh.close()

    def __enter__(self) -> EventLog:
        """Return self for use in a `with` block."""
        return self

    def __exit__(self, *exc_info: object) -> None:
        """Flush and close on context exit."""
        self.close()


__all__ = ["EventLog"]
