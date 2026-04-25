"""Pydantic v2 models for Kata 1.

Why every boundary is a pydantic model: Constitution Principle II
(Schema-Enforced Boundaries, NON-NEGOTIABLE) — invalid payloads MUST raise
immediately rather than be best-effort parsed. Tool inputs, tool outputs, and
event-log records all flow through `model_validate` / `model_dump_json` so
malformed data fails the run loud (FR-008).

The model surface here mirrors `specs/001-agentic-loop/data-model.md` and the
JSON Schemas under `specs/001-agentic-loop/contracts/`. If you change a field,
also update those documents (Principle VIII — docs and code move together).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --------------------------------------------------------------------------- #
# Stop-signal surfaces                                                        #
# --------------------------------------------------------------------------- #

# Why a Literal type instead of a str: branching logic in loop.py exhaustively
# matches on this enumeration. A typo in one branch then surfaces as a type-
# checker error rather than as a silent fall-through (Principle I).
StopSignal = Literal["tool_use", "end_turn", "max_tokens", "stop_sequence"]

# Why an explicit "absent_signal" / "unhandled_signal" surface: FR-006 forbids
# silently mapping unknown values to known ones. Routing them through a
# distinct type makes their handling visible at every call site.
UnhandledSignalLabel = Literal["unhandled_signal", "absent_signal"]


class UnhandledStopSignal(BaseModel):
    """Carrier for any stop_reason value the loop does not explicitly handle.

    Why this is a model and not just a string: it pairs the *reason label* with
    the *raw value* so the event log captures both — supporting Principle VII
    (Provenance & Self-Audit) and SC-006.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    raw_value: str | None = Field(
        default=None,
        description="Exact stop_reason returned by the API, or None if absent.",
    )
    reason_label: UnhandledSignalLabel


# --------------------------------------------------------------------------- #
# Tool surfaces                                                               #
# --------------------------------------------------------------------------- #


class ToolDefinition(BaseModel):
    """A tool registered with an AgentSession.

    Why immutable / frozen: Constitution forbids mid-session tool registration
    because it would silently change the set of valid `tool_use` payloads
    mid-replay and break SC-007 (byte-identical reruns).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z][a-zA-Z0-9_-]{0,63}$")
    description: str = Field(min_length=1)
    input_schema: dict[str, Any]


class ToolCall(BaseModel):
    """One tool_use block extracted from a Claude response.

    Why we do not derive the tool to call from response prose: FR-004. The
    `tool_name` field is the structured signal; reading the assistant's text
    to second-guess it would be precisely the anti-pattern this kata exists
    to defend against.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_use_id: str = Field(min_length=1)
    tool_name: str = Field(min_length=1)
    input: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Result of executing a ToolCall, appended to conversation history.

    Why `status` is a Literal, not a free string: FR-007 — the loop branches
    on this field. A typo would silently route an error through the success
    path, exactly the failure mode a schema is meant to prevent.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_use_id: str = Field(min_length=1)
    status: Literal["ok", "error"]
    output: Any = None
    error_category: str | None = None

    @model_validator(mode="after")
    def _check_error_category(self) -> ToolResult:
        # Why both directions are enforced: ok+error_category or error+null
        # would each break the contract in tool-result.schema.json. Failing
        # construction here means we cannot accidentally append a malformed
        # ToolResult to history.
        if self.status == "error" and not self.error_category:
            raise ValueError("error_category is required when status=='error'")
        if self.status == "ok" and self.error_category is not None:
            raise ValueError("error_category MUST be null when status=='ok'")
        return self


# --------------------------------------------------------------------------- #
# Turn + Event log                                                            #
# --------------------------------------------------------------------------- #


class Turn(BaseModel):
    """One agent response cycle.

    Why `assistant_text_blocks` is captured but never consulted by control
    flow: it is recorded only for human review and live-API debugging. The
    AST lint test (`tests/.../lint/test_no_prose_matching.py`) makes reading
    it from `loop.py` an instant build failure — encoding the rule in code
    rather than documentation alone.
    """

    model_config = ConfigDict(extra="forbid")

    iteration: int = Field(ge=0)
    stop_signal: StopSignal | UnhandledStopSignal
    tool_calls: list[ToolCall] = Field(default_factory=list)
    assistant_text_blocks: list[str] = Field(default_factory=list)
    response_id: str = Field(min_length=1)


# Why TerminationReason is a separate Literal: FR-005 mandates a labeled cause
# on the terminal iteration. Keeping the closed set in one place means a new
# reason cannot be introduced without also updating the JSON Schema and the
# data-model doc — Principle VIII keeps them coupled.
TerminationReason = Literal[
    "end_turn",
    "unhandled_signal",
    "absent_signal",
    "max_tokens",
    "stop_sequence",
    "malformed_tool_use",
    "tool_error_unrecoverable",
]


BranchTaken = Literal["tool_dispatch", "terminate", "halt_unhandled"]


class EventRecord(BaseModel):
    """One JSONL line emitted per loop iteration.

    Why `extra='forbid'`: data-model.md mandates that no text-derived field
    (e.g. `prose_excerpt`, `completion_hint`) is allowed. The schema is the
    enforcement: pydantic rejects unknown keys at construction time.
    """

    model_config = ConfigDict(extra="forbid")

    session_id: str
    iteration: int = Field(ge=0)
    timestamp: datetime
    stop_signal: str
    branch_taken: BranchTaken
    tool_name: str | None = None
    tool_outcome: Literal["ok", "error"] | None = None
    termination_cause: TerminationReason | None = None

    @field_validator("timestamp")
    @classmethod
    def _ensure_utc(cls, value: datetime) -> datetime:
        # Why we coerce to UTC: SC-007 requires byte-identical event logs across
        # reruns. Mixed-tz timestamps would break that diff for no semantic gain.
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def _branch_invariants(self) -> EventRecord:
        # Why these invariants live here: the JSON Schema enforces them on
        # disk; the model enforces them in memory. Two layers, one truth.
        if self.branch_taken == "tool_dispatch":
            if not self.tool_name or self.tool_outcome is None:
                raise ValueError("branch_taken='tool_dispatch' requires tool_name + tool_outcome")
        if self.branch_taken in ("terminate", "halt_unhandled") and self.termination_cause is None:
            raise ValueError(
                "branch_taken in {terminate, halt_unhandled} requires termination_cause"
            )
        return self


# --------------------------------------------------------------------------- #
# Session                                                                     #
# --------------------------------------------------------------------------- #


class AgentSession(BaseModel):
    """One workshop run.

    Why session_id is set at construction and never mutated: it names the
    runs/<session_id>/ directory holding the event log. Mutating it would
    orphan the log mid-run.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    session_id: str = Field(default_factory=lambda: str(uuid4()))
    model: str
    registered_tools: list[ToolDefinition]
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    termination: TerminationReason | None = None

    @field_validator("registered_tools")
    @classmethod
    def _no_duplicate_tool_names(cls, tools: list[ToolDefinition]) -> list[ToolDefinition]:
        # Why we reject duplicates at construction: the loop dispatches by
        # name. Two registrations under the same name would make dispatch
        # non-deterministic — exactly what Principle I forbids.
        names = [t.name for t in tools]
        if len(names) != len(set(names)):
            raise ValueError("registered_tools contains duplicate names")
        return tools


__all__ = [
    "AgentSession",
    "BranchTaken",
    "EventRecord",
    "StopSignal",
    "TerminationReason",
    "ToolCall",
    "ToolDefinition",
    "ToolResult",
    "Turn",
    "UnhandledStopSignal",
]
