"""Runtime session glue: ties EventLog + ToolRegistry + conversation history.

Why this is a thin runtime class instead of stuffing fields onto the pydantic
`AgentSession` model: the model captures *data* about a session (id, model
name, tool definitions, termination reason). The runtime owns *resources*
(open file handle, mutable history buffer) — mixing the two would force the
data model to relax its `frozen=True` invariants and lose Principle II's
guarantees.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from katas.kata_001_agentic_loop.events import EventLog
from katas.kata_001_agentic_loop.models import AgentSession, ToolDefinition
from katas.kata_001_agentic_loop.tools import ToolRegistry


class RuntimeSession:
    """Wires together everything one kata run needs.

    The class is intentionally tiny: it holds references and exposes the
    `record` (data), `registry` (dispatch), and `event_log` (audit) collabo-
    rators. The loop pulls them apart and drives them — keeping coordination
    logic in `loop.py` and not here (single-responsibility per Constitution
    §Development Workflow / artifact ownership).
    """

    def __init__(
        self,
        *,
        model: str,
        tool_definitions: list[ToolDefinition],
        registry: ToolRegistry,
        runs_root: str | Path = "runs",
    ) -> None:
        """Build the AgentSession record and open its event log."""
        # Why we construct the pydantic record FIRST: we need its
        # `session_id` to derive the run directory. If construction failed,
        # nothing has touched the filesystem yet.
        self.record: AgentSession = AgentSession(
            model=model,
            registered_tools=tool_definitions,
        )
        self.registry: ToolRegistry = registry
        self.history: list[dict[str, Any]] = []
        run_dir = Path(runs_root) / self.record.session_id
        self.event_log: EventLog = EventLog(run_dir / "events.jsonl")
        self._history_path: Path = run_dir / "history.json"

    @property
    def session_id(self) -> str:
        """UUID of the underlying AgentSession record."""
        return self.record.session_id

    def append_history(self, entry: dict[str, Any]) -> None:
        """Append one role-tagged entry to the in-memory conversation history."""
        # Why a method (not direct list mutation by callers): centralising
        # writes makes it possible to mirror history to disk later (FR-010
        # replayability) without changing every call site.
        self.history.append(entry)

    def close(self, *, termination: str | None = None) -> None:
        """Finalize the run.

        Why we mirror `history.json` only on close: the live conversation
        history is held in memory during a run for speed; persisting once at
        the end gives FR-010 replay support without extra disk pressure.
        """
        if termination:
            # AgentSession is not frozen — its ConfigDict only sets
            # extra="forbid". Mutating `termination` + `completed_at` here
            # mirrors the pydantic v2 invariant in data-model.md
            # ("completed_at populated on terminal halt").
            self.record.termination = termination  # type: ignore[assignment]
            self.record.completed_at = datetime.now(UTC)
        try:
            self._history_path.write_text(json.dumps(self.history, indent=2, ensure_ascii=False))
        finally:
            self.event_log.close()


__all__ = ["RuntimeSession"]
