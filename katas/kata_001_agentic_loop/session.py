"""Runtime session wiring.

Why this exists separately from ``models.AgentSession``:
    ``AgentSession`` is a serialisable pydantic model used for assertions
    and audit. The actual runtime needs three live pieces of state — the
    open ``EventLog``, the in-memory conversation ``history``, and the
    ``ToolRegistry`` — that don't belong on a frozen pydantic model. Keeping
    the runtime here means the loop module stays a pure function over its
    inputs (Constitution Principle I — observable transitions).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .client import AnthropicClient
from .events import EventLog
from .models import AgentSession, ToolDefinition
from .tools import ToolRegistry


@dataclass
class RuntimeSession:
    """All mutable state needed to run one kata session.

    The loop reads from / writes to this object. Two runs sharing one
    ``RuntimeSession`` would clobber each other's history, which is precisely
    why session construction also creates the per-session ``runs/<id>/``
    directory.
    """

    session_id: str
    model: str
    client: AnthropicClient
    registry: ToolRegistry
    event_log: EventLog
    history: list[dict[str, Any]] = field(default_factory=list)
    started_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    completed_at: datetime | None = None
    termination: str | None = None

    @classmethod
    def open(
        cls,
        *,
        session_id: str,
        model: str,
        client: AnthropicClient,
        runs_root: Path,
        tool_definitions: list[tuple[ToolDefinition, Any]] | None = None,
    ) -> RuntimeSession:
        """Construct a session, register tools, and open the event log."""
        registry = ToolRegistry()
        for definition, impl in tool_definitions or []:
            registry.register(definition, impl)
        log = EventLog(runs_root=runs_root, session_id=session_id)
        return cls(
            session_id=session_id,
            model=model,
            client=client,
            registry=registry,
            event_log=log,
        )

    def to_metadata(self) -> AgentSession:
        """Snapshot serialisable metadata (used for audit + tests)."""
        return AgentSession(
            session_id=self.session_id,
            model=self.model,
            registered_tools=self.registry.definitions,
            started_at=self.started_at,
            completed_at=self.completed_at,
            termination=self.termination,  # type: ignore[arg-type]
        )

    def close(self) -> None:
        """Flush + close the event log."""
        self.event_log.close()
