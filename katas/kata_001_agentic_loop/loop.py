"""The signal-driven agentic loop.

Why this module looks small: the kata's whole pedagogy is "the loop is a
switch on `stop_reason`". Anything beyond that (retries, backoff, parallel
tool dispatch, prose interpretation) would dilute the lesson and is
intentionally out of scope (plan.md Complexity Tracking).

Constitutional anchors:
- Principle I (Determinism Over Probability, NN) — branching keys off
  `Turn.stop_signal` only; `Turn.assistant_text_blocks` is never read here.
  The AST lint at `tests/.../lint/test_no_prose_matching.py` enforces it.
- Principle II (Schema-Enforced Boundaries, NN) — every payload entering or
  leaving the loop is a pydantic model.
- Principle VII (Provenance & Self-Audit) — exactly one EventRecord per
  iteration; the terminal record carries the labeled cause.

This module deliberately does NOT import `re`, `string.find`, `startswith`,
`endswith`, or use the `in` operator on a string literal. Adding any of those
makes the lint test fail.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from katas.kata_001_agentic_loop.client import MessagesClient, RawResponse
from katas.kata_001_agentic_loop.models import (
    EventRecord,
    StopSignal,
    TerminationReason,
    ToolCall,
    Turn,
    UnhandledStopSignal,
)
from katas.kata_001_agentic_loop.session import RuntimeSession
from katas.kata_001_agentic_loop.tools import MalformedToolUse


# Why a Set, not a list, of recognized literal values: O(1) membership check
# without the `in <string>` anti-pattern catching us out — this is a Set of
# strings, not substring search. The AST lint flags ONLY string-literal
# comparisons, which this is not.
_RECOGNIZED_SIGNALS: frozenset[str] = frozenset(
    {"tool_use", "end_turn", "max_tokens", "stop_sequence"}
)


def _classify(stop_reason: str | None) -> StopSignal | UnhandledStopSignal:
    """Map a raw `stop_reason` to a typed branching input.

    Why this returns a union: FR-006 forbids silently mapping unknown values
    to known ones. `UnhandledStopSignal` carries the raw value so the event
    log retains audit-grade provenance even when the value is foreign.
    """
    if stop_reason is None:
        return UnhandledStopSignal(raw_value=None, reason_label="absent_signal")
    # Set membership on the recognized set is structural, not text-search.
    if stop_reason not in _RECOGNIZED_SIGNALS:
        return UnhandledStopSignal(
            raw_value=stop_reason, reason_label="unhandled_signal"
        )
    # Cast: stop_reason is now narrowed by structure to one of the literals.
    return stop_reason  # type: ignore[return-value]


def _extract_tool_calls(content: list[dict[str, Any]]) -> list[ToolCall]:
    """Pull `tool_use` blocks out of a Messages-API content array.

    Why we read `block["type"]` (a structured key) and never `block["text"]`:
    block kind is metadata; block text is prose. Switching on metadata keeps
    Principle I intact.
    """
    calls: list[ToolCall] = []
    for block in content:
        if block.get("type") == "tool_use":
            calls.append(
                ToolCall(
                    tool_use_id=str(block.get("id", "")),
                    tool_name=str(block.get("name", "")),
                    input=dict(block.get("input", {})),
                )
            )
    return calls


def _assistant_text_blocks(content: list[dict[str, Any]]) -> list[str]:
    """Collect text blocks for the audit log only.

    Why we still capture them: they go into `Turn.assistant_text_blocks` so a
    human reviewing the run can see what the model said. They are NEVER read
    by the loop — the AST lint guarantees that.
    """
    out: list[str] = []
    for block in content:
        if block.get("type") == "text":
            out.append(str(block.get("text", "")))
    return out


def _emit(
    session: RuntimeSession,
    *,
    iteration: int,
    stop_signal: StopSignal | UnhandledStopSignal,
    branch: str,
    tool_name: str | None = None,
    tool_outcome: str | None = None,
    termination_cause: TerminationReason | None = None,
) -> None:
    """Single chokepoint for event-log emission.

    Why centralized: the EventRecord schema is strict (data-model.md). One
    constructor here means a missing field becomes a typed error at the
    closest possible point to the cause.
    """
    if isinstance(stop_signal, UnhandledStopSignal):
        signal_str = stop_signal.reason_label
    else:
        signal_str = stop_signal
    session.event_log.emit(
        EventRecord(
            session_id=session.session_id,
            iteration=iteration,
            timestamp=datetime.now(timezone.utc),
            stop_signal=signal_str,
            branch_taken=branch,  # type: ignore[arg-type]
            tool_name=tool_name,
            tool_outcome=tool_outcome,  # type: ignore[arg-type]
            termination_cause=termination_cause,
        )
    )


def run(
    *,
    session: RuntimeSession,
    client: MessagesClient,
    initial_user_message: str,
    max_iterations: int = 32,
) -> TerminationReason:
    """Drive the session until a terminal stop_signal lands.

    Why `max_iterations` is finite (32, not unbounded): a defective fixture
    or a runaway live session must not loop forever. 32 is a workshop ceiling
    — far above any kata fixture and far below "burn the API budget". The
    cap surfaces as a `tool_error_unrecoverable` termination, surfacing in
    the log instead of silently halting.
    """
    # Why we seed history with the user message before the first turn:
    # FR-010 — the conversation history is the replayable record. The user
    # turn is part of that history, even though it isn't an SDK response.
    session.append_history({"role": "user", "content": initial_user_message})

    for iteration in range(max_iterations):
        response: RawResponse = client.send(
            model=session.record.model,
            messages=list(session.history),
            tools=session.registry.to_anthropic_tools(),
        )
        signal = _classify(response.stop_reason)
        text_blocks = _assistant_text_blocks(response.content)
        tool_calls = _extract_tool_calls(response.content)

        # Why we construct a Turn even though the loop never *reads* its text
        # blocks: Turn is the audit-ready snapshot of the response. Building
        # it forces validation, locking in Principle II at the boundary.
        Turn(
            iteration=iteration,
            stop_signal=signal,
            tool_calls=tool_calls,
            assistant_text_blocks=text_blocks,
            response_id=response.response_id,
        )

        # Append the assistant turn before any branching — keeps history in
        # source order regardless of which branch fires (FR-010).
        session.append_history(
            {
                "role": "assistant",
                "content": response.content,
                "stop_reason": response.stop_reason,
            }
        )

        if isinstance(signal, UnhandledStopSignal):
            cause: TerminationReason = signal.reason_label  # type: ignore[assignment]
            _emit(
                session,
                iteration=iteration,
                stop_signal=signal,
                branch="halt_unhandled",
                termination_cause=cause,
            )
            return cause

        # signal is now a StopSignal literal. Branch by structural equality
        # against the closed set — never against text content.
        if signal == "tool_use":
            try:
                _dispatch_tool_calls(session, tool_calls, iteration=iteration)
            except MalformedToolUse:
                _emit(
                    session,
                    iteration=iteration,
                    stop_signal=signal,
                    branch="terminate",
                    termination_cause="malformed_tool_use",
                )
                return "malformed_tool_use"
            # Continue the loop: no termination decision is made on tool_use.
            continue
        if signal == "end_turn":
            _emit(
                session,
                iteration=iteration,
                stop_signal=signal,
                branch="terminate",
                termination_cause="end_turn",
            )
            return "end_turn"
        if signal == "max_tokens":
            _emit(
                session,
                iteration=iteration,
                stop_signal=signal,
                branch="terminate",
                termination_cause="max_tokens",
            )
            return "max_tokens"
        if signal == "stop_sequence":
            _emit(
                session,
                iteration=iteration,
                stop_signal=signal,
                branch="terminate",
                termination_cause="stop_sequence",
            )
            return "stop_sequence"

        # Unreachable: _classify returned a Literal we have not branched on.
        # Treat as unhandled to preserve Principle I rather than fall through.
        _emit(
            session,
            iteration=iteration,
            stop_signal=signal,
            branch="halt_unhandled",
            termination_cause="unhandled_signal",
        )
        return "unhandled_signal"

    # max_iterations exhausted without a terminal signal.
    _emit(
        session,
        iteration=max_iterations,
        stop_signal=UnhandledStopSignal(
            raw_value=None, reason_label="unhandled_signal"
        ),
        branch="halt_unhandled",
        termination_cause="tool_error_unrecoverable",
    )
    return "tool_error_unrecoverable"


def _dispatch_tool_calls(
    session: RuntimeSession,
    calls: list[ToolCall],
    *,
    iteration: int,
) -> None:
    """Run every tool_use block on the turn and append results to history.

    Why each call gets its own EventRecord: data-model.md says exactly one
    record per iteration, but a turn may carry multiple tool_use blocks.
    Recording one record per call (with iteration tied to the loop step) is
    the closest faithful reading of FR-005 — every tool invocation is
    individually auditable.
    """
    if not calls:
        # An "empty tool_use" turn is malformed: FR-008 says halt with label.
        raise MalformedToolUse("tool_use turn carried no tool_use blocks")
    for call in calls:
        # validate_call raises MalformedToolUse on unknown tool / bad input.
        session.registry.validate_call(call)
        result = session.registry.dispatch(call)
        # Why we append the tool_result block in the SDK shape: the next
        # iteration sends `messages` straight back to Claude; the SDK requires
        # the tool result encoded as a content block with type "tool_result".
        session.append_history(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": result.tool_use_id,
                        "content": _serialize_tool_output(result.output),
                        "is_error": result.status == "error",
                    }
                ],
            }
        )
        _emit(
            session,
            iteration=iteration,
            stop_signal="tool_use",
            branch="tool_dispatch",
            tool_name=call.tool_name,
            tool_outcome=result.status,
        )


def _serialize_tool_output(output: Any) -> str:
    """Convert a tool's return value to a string the SDK accepts.

    Why json over repr: deterministic, language-neutral, and round-trips
    through any reviewer's tooling.
    """
    import json  # noqa: PLC0415

    if isinstance(output, str):
        return output
    return json.dumps(output, sort_keys=True, ensure_ascii=False)


__all__ = ["run"]
