"""Pydantic v2 entities crossing the loop's API boundaries.

Why each model exists:
    Constitution Principle II (Schema-Enforced Boundaries) requires that every
    payload that crosses an interface — tool definition, tool call, tool
    result, conversation turn, event-log line — be validated on construction.
    Letting these boundaries float as ``dict`` is exactly the failure mode the
    kata is built to prevent: silent mis-shaped objects that look fine until
    a downstream branch silently does the wrong thing.

The :class:`Turn` model deliberately keeps ``assistant_text_blocks`` so the
event log can record what the model said, but :mod:`katas.kata_001_agentic_loop.loop`
MUST NOT branch on that field — a separate AST lint test enforces that
constraint (Principle I).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Closed set of structured stop signals the Messages API returns. Any value
# outside this set surfaces as ``UnhandledStopSignal`` so the loop can halt
# with a labeled cause instead of falling into a default-no-op (FR-006).
StopSignal = Literal["tool_use", "end_turn", "max_tokens", "stop_sequence"]

# All recognized terminal causes. Each leaf branch in ``loop.run`` must map
# to exactly one of these — never an open-ended string (Principle II).
TerminationReason = Literal[
    "end_turn",
    "unhandled_signal",
    "absent_signal",
    "max_tokens",
    "stop_sequence",
    "malformed_tool_use",
    "tool_error_unrecoverable",
]


class UnhandledStopSignal(BaseModel):
    """Surface for stop signals we did not whitelist.

    Why a class instead of a sentinel string: tests need to know whether the
    field was missing entirely (``raw_value is None``) or returned a value the
    loop does not handle (``raw_value`` set). Conflating those two would
    erase signal needed by FR-006.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_value: str | None = Field(
        default=None,
        description="Exact value the API returned; None if the field was absent.",
    )
    reason_label: Literal["unhandled_signal", "absent_signal"]


class ToolDefinition(BaseModel):
    """One tool registered with the session — handed to the SDK + dispatcher."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1)
    input_schema: dict[str, Any] = Field(
        description="JSON Schema validated against ToolCall.input before dispatch.",
    )

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        # Why: SDK rejects names outside this charset; failing here gives the
        # workshop a readable error instead of an opaque API 400 later.
        import re as _re  # noqa: PLC0415 — kept inside validator so loop.py stays re-free

        if not _re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", value):
            raise ValueError(f"invalid tool name: {value!r}")
        return value


class ToolCall(BaseModel):
    """A tool_use block extracted from a model response."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_use_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Outcome of dispatching one :class:`ToolCall`.

    Invariants (mirrors ``contracts/tool-result.schema.json``):
        - ``status="error"``  -> ``error_category`` MUST be a non-empty string.
        - ``status="ok"``     -> ``error_category`` MUST be ``None``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_use_id: str
    status: Literal["ok", "error"]
    output: Any = None
    error_category: str | None = None

    @field_validator("error_category")
    @classmethod
    def _category_matches_status(cls, value: str | None, info) -> str | None:
        status = info.data.get("status")
        if status == "error":
            if not value:
                raise ValueError("error_category required when status='error'")
        elif status == "ok" and value is not None:
            raise ValueError("error_category must be None when status='ok'")
        return value


class Turn(BaseModel):
    """One response cycle from the Messages API."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    iteration: int = Field(ge=0)
    stop_signal: StopSignal | UnhandledStopSignal
    tool_calls: list[ToolCall] = Field(default_factory=list)
    # Stored ONLY for audit / logging — loop.py is forbidden from reading this.
    assistant_text_blocks: list[str] = Field(default_factory=list)
    response_id: str = ""


class EventRecord(BaseModel):
    """One JSONL line in ``runs/<session_id>/events.jsonl``.

    ``extra="forbid"`` is load-bearing: it is the structural defence against
    accidentally adding a text-derived field (``prose_excerpt`` etc.) which
    would re-introduce the very anti-pattern the kata is supposed to prevent
    (Principle I).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str
    iteration: int = Field(ge=0)
    timestamp: datetime
    stop_signal: Literal[
        "tool_use",
        "end_turn",
        "max_tokens",
        "stop_sequence",
        "unhandled_signal",
        "absent_signal",
    ]
    branch_taken: Literal["tool_dispatch", "terminate", "halt_unhandled"]
    tool_name: str | None = None
    tool_outcome: Literal["ok", "error"] | None = None
    termination_cause: TerminationReason | None = None

    @field_validator("timestamp")
    @classmethod
    def _force_utc(cls, value: datetime) -> datetime:
        # Why: SC-007 demands byte-identical event logs across runs; a naive or
        # local-tz timestamp would make that diff fail on CI vs. dev machines.
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class AgentSession(BaseModel):
    """High-level metadata about one kata run.

    The runtime wiring (event log, tool registry, history) lives on
    :class:`katas.kata_001_agentic_loop.session.RuntimeSession` to keep this
    model strictly serialisable. Tests use both: the dataclass for assertions,
    the runtime object for orchestration.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    session_id: str
    model: str
    registered_tools: list[ToolDefinition]
    started_at: datetime
    completed_at: datetime | None = None
    termination: TerminationReason | None = None
