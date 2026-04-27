"""The agentic loop — the only file this entire kata is really about.

Why this file exists:
    Constitution Principle I (Determinism Over Probability) demands that
    agent control flow be driven by structured signals, never by string
    matching over response prose. ``run`` is that single decision point: it
    inspects ``response.stop_reason``, picks one of five branches, and emits
    a labelled ``EventRecord`` either way.

Hard constraints enforced here AND by ``tests/katas/kata_001_agentic_loop/lint``:
    - This module MUST NOT import ``re`` or any pattern-matching library.
    - This module MUST NOT call ``.find / .index / .search / .match`` on text.
    - This module MUST NOT use ``in`` against a string literal on response text.
    - The dispatcher MUST never inspect ``Turn.assistant_text_blocks`` to make
      a routing decision — that field exists only for the event-log audit.
"""

from __future__ import annotations

from typing import Any

from .events import EventLog
from .models import (
    EventRecord,
    StopSignal,
    TerminationReason,
    ToolCall,
    Turn,
    UnhandledStopSignal,
)
from .session import RuntimeSession
from .tools import MalformedToolUse

# Closed whitelist of structurally-valid stop signals. Built once at import
# time so the membership test below is a fixed-set lookup, not a string scan.
_RECOGNIZED_SIGNALS: frozenset[str] = frozenset(
    {"tool_use", "end_turn", "max_tokens", "stop_sequence"}
)


def classify_stop_signal(raw: str | None) -> StopSignal | UnhandledStopSignal:
    """Map the SDK's ``stop_reason`` value to a typed signal.

    Why a function: every code path that needs to make a decision goes
    through here, so adding a new recognised signal is a single edit and
    the AST lint can keep treating ``loop.py`` as branch-only logic.
    """
    if raw is None:
        return UnhandledStopSignal(raw_value=None, reason_label="absent_signal")
    # Membership test against a frozenset — NOT a substring/regex search.
    if raw not in _RECOGNIZED_SIGNALS:
        return UnhandledStopSignal(raw_value=raw, reason_label="unhandled_signal")
    return raw  # type: ignore[return-value]


def extract_tool_calls(content_blocks: list[dict[str, Any]]) -> list[ToolCall]:
    """Pull ``tool_use`` blocks out of a response payload.

    Validation of *which* tool is being called and *whether* the input
    matches its declared schema happens later, in
    :meth:`ToolRegistry.dispatch`. This function is intentionally just a
    typed projection — the loop does not interpret tool_use payloads.
    """
    calls: list[ToolCall] = []
    for block in content_blocks:
        if block.get("type") != "tool_use":
            continue
        # Pydantic raises a ValidationError if the block lacks required
        # fields — the loop translates that into a malformed_tool_use halt.
        calls.append(
            ToolCall(
                tool_use_id=block.get("id", ""),
                tool_name=block.get("name", ""),
                input=block.get("input", {}) or {},
            )
        )
    return calls


def build_turn(iteration: int, response: Any) -> Turn:
    """Construct an immutable :class:`Turn` from one ``RawResponse``."""
    text_blocks: list[str] = []
    for block in response.content:
        if block.get("type") == "text":
            text_blocks.append(block.get("text", ""))
    signal = classify_stop_signal(response.stop_reason)
    tool_calls: list[ToolCall] = []
    if signal == "tool_use":
        tool_calls = extract_tool_calls(list(response.content))
    return Turn(
        iteration=iteration,
        stop_signal=signal,
        tool_calls=tool_calls,
        assistant_text_blocks=text_blocks,
        response_id=response.id,
    )


def _emit_terminate(
    log: EventLog,
    *,
    session_id: str,
    iteration: int,
    stop_signal_str: str,
    cause: TerminationReason,
    branch: str = "terminate",
) -> None:
    """Record the terminal iteration and flush. Single call per session."""
    record = EventRecord(
        session_id=session_id,
        iteration=iteration,
        timestamp=log.stamp(),
        stop_signal=stop_signal_str,  # type: ignore[arg-type]
        branch_taken=branch,  # type: ignore[arg-type]
        termination_cause=cause,
    )
    log.emit(record)


def _emit_tool_dispatch(
    log: EventLog,
    *,
    session_id: str,
    iteration: int,
    tool_name: str,
    tool_outcome: str,
) -> None:
    """Record one tool_dispatch iteration."""
    record = EventRecord(
        session_id=session_id,
        iteration=iteration,
        timestamp=log.stamp(),
        stop_signal="tool_use",
        branch_taken="tool_dispatch",
        tool_name=tool_name,
        tool_outcome=tool_outcome,  # type: ignore[arg-type]
    )
    log.emit(record)


def run(
    session: RuntimeSession,
    initial_user_message: str,
    *,
    max_iterations: int = 32,
) -> TerminationReason:
    """Drive the agentic loop until a terminal signal fires.

    Returns the :data:`TerminationReason` the run halted on. ``max_iterations``
    is a defensive guard rail — under correct fixtures the loop always
    terminates first; an exhausted budget surfaces as
    ``tool_error_unrecoverable`` (per data-model.md).
    """
    # Seed conversation history. ``history`` is the SDK ``messages=`` array.
    session.history.append({"role": "user", "content": initial_user_message})

    iteration = 0
    while iteration < max_iterations:
        response = session.client.send(
            messages=session.history,
            tools=session.registry.as_sdk_tools(),
        )
        turn = build_turn(iteration, response)

        # Mirror the assistant turn into history — required by Messages API
        # for the next request to be valid.
        session.history.append({"role": "assistant", "content": list(response.content)})

        signal = turn.stop_signal

        # ── Branch 1: tool_use — dispatch + continue ────────────────────────
        if signal == "tool_use":
            try:
                # Dispatch every requested tool; append a tool_result block
                # to history for each. Routine tool errors are captured as
                # ``ToolResult(status="error")`` and the loop *continues*.
                tool_result_blocks: list[dict[str, Any]] = []
                last_outcome = "ok"
                last_name = ""
                for call in turn.tool_calls:
                    result = session.registry.dispatch(call)
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": result.tool_use_id,
                            "content": result.output
                            if isinstance(result.output, str)
                            else _coerce_output(result.output),
                            "is_error": result.status == "error",
                        }
                    )
                    last_name = call.tool_name
                    last_outcome = result.status
                if tool_result_blocks:
                    session.history.append({"role": "user", "content": tool_result_blocks})
                _emit_tool_dispatch(
                    session.event_log,
                    session_id=session.session_id,
                    iteration=iteration,
                    tool_name=last_name,
                    tool_outcome=last_outcome,
                )
            except MalformedToolUse:
                _emit_terminate(
                    session.event_log,
                    session_id=session.session_id,
                    iteration=iteration,
                    stop_signal_str="tool_use",
                    cause="malformed_tool_use",
                    branch="halt_unhandled",
                )
                session.termination = "malformed_tool_use"
                return "malformed_tool_use"
            iteration += 1
            continue

        # ── Branch 2: end_turn — clean halt ─────────────────────────────────
        if signal == "end_turn":
            _emit_terminate(
                session.event_log,
                session_id=session.session_id,
                iteration=iteration,
                stop_signal_str="end_turn",
                cause="end_turn",
            )
            session.termination = "end_turn"
            return "end_turn"

        # ── Branch 3: max_tokens — halt with labelled cause ─────────────────
        if signal == "max_tokens":
            _emit_terminate(
                session.event_log,
                session_id=session.session_id,
                iteration=iteration,
                stop_signal_str="max_tokens",
                cause="max_tokens",
            )
            session.termination = "max_tokens"
            return "max_tokens"

        # ── Branch 4: stop_sequence — halt with labelled cause ──────────────
        if signal == "stop_sequence":
            _emit_terminate(
                session.event_log,
                session_id=session.session_id,
                iteration=iteration,
                stop_signal_str="stop_sequence",
                cause="stop_sequence",
            )
            session.termination = "stop_sequence"
            return "stop_sequence"

        # ── Branch 5: unhandled / absent — protocol-violation halt ──────────
        # ``signal`` is an UnhandledStopSignal at this point — its
        # ``reason_label`` field tells us which terminal bucket to report.
        unhandled: UnhandledStopSignal = signal  # type: ignore[assignment]
        cause: TerminationReason = unhandled.reason_label
        stop_signal_str = "absent_signal" if cause == "absent_signal" else "unhandled_signal"
        _emit_terminate(
            session.event_log,
            session_id=session.session_id,
            iteration=iteration,
            stop_signal_str=stop_signal_str,
            cause=cause,
            branch="halt_unhandled",
        )
        session.termination = cause
        return cause

    # Defensive: budget exhausted without a terminal signal.
    _emit_terminate(
        session.event_log,
        session_id=session.session_id,
        iteration=iteration,
        stop_signal_str="unhandled_signal",
        cause="tool_error_unrecoverable",
        branch="halt_unhandled",
    )
    session.termination = "tool_error_unrecoverable"
    return "tool_error_unrecoverable"


def _coerce_output(value: Any) -> str:
    """Render non-string tool outputs to a JSON string for the API.

    Why: the SDK accepts ``content`` as a string per tool_result block. We
    serialise via ``json.dumps`` (deterministic key order) so two runs with
    the same dict output produce identical history bytes.
    """
    import json as _json  # noqa: PLC0415 — keep loop.py minimal at top-level

    return _json.dumps(value, sort_keys=True, ensure_ascii=True)
