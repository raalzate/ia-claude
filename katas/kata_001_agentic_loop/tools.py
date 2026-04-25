"""Tool registry + dispatch for Kata 1.

Why this is a standalone module (not glued into loop.py): the registry's
contract is "a `tool_use` block names a registered tool, the registry runs
it, returns a structured `ToolResult`". Keeping it isolated means the loop
never has to know how a tool is implemented — it only needs the result.

Constitutional anchor: FR-007 (errors are structured, never inferred from
text) and FR-008 (malformed payloads halt loud, never best-effort recovered).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from jsonschema import ValidationError, validate

from katas.kata_001_agentic_loop.models import (
    ToolCall,
    ToolDefinition,
    ToolResult,
)


class MalformedToolUse(Exception):
    """Raised when a tool_use payload cannot be dispatched.

    Why a dedicated exception: FR-008 wants the loop to halt with a labeled
    `malformed_tool_use` termination reason. Catching a generic Exception
    would hide structural mismatches (unknown tool, schema-failed input)
    behind generic error handling.
    """

    def __init__(self, reason: str, *, tool_name: str | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.tool_name = tool_name


class ToolRegistry:
    """Maps registered tools to their handlers.

    Why we hold handlers separate from `ToolDefinition`: the definition is
    a pydantic model passed to the model API as schema metadata; the handler
    is local Python. Keeping them in two collections preserves the model's
    immutability (Principle II — schemas don't carry executables).
    """

    def __init__(self) -> None:
        self._defs: dict[str, ToolDefinition] = {}
        self._handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}

    def register(
        self,
        definition: ToolDefinition,
        handler: Callable[[dict[str, Any]], Any],
    ) -> None:
        # Why duplicate names raise instead of overwrite: silent overwrite
        # would make the dispatch target depend on registration order — a
        # hidden source of non-determinism (Principle I).
        if definition.name in self._defs:
            raise ValueError(f"tool already registered: {definition.name}")
        self._defs[definition.name] = definition
        self._handlers[definition.name] = handler

    @property
    def definitions(self) -> list[ToolDefinition]:
        # Why we return a fresh list: callers (loop.py) pass this to the
        # client without mutating it; an internal mutation here would
        # otherwise leak across iterations.
        return list(self._defs.values())

    def to_anthropic_tools(self) -> list[dict[str, Any]]:
        """Serialize registered tools in the shape the Anthropic SDK expects."""
        return [
            {
                "name": d.name,
                "description": d.description,
                "input_schema": d.input_schema,
            }
            for d in self._defs.values()
        ]

    def validate_call(self, call: ToolCall) -> None:
        """Raise MalformedToolUse if `call` cannot be dispatched.

        Why this is separate from `dispatch`: the loop checks validity *before*
        committing to dispatch so it can emit a `malformed_tool_use`
        termination cause without having executed any handler (FR-008).
        """
        definition = self._defs.get(call.tool_name)
        if definition is None:
            raise MalformedToolUse(
                f"unknown tool: {call.tool_name!r}", tool_name=call.tool_name
            )
        try:
            validate(instance=call.input, schema=definition.input_schema)
        except ValidationError as exc:
            raise MalformedToolUse(
                f"input failed schema for {call.tool_name!r}: {exc.message}",
                tool_name=call.tool_name,
            ) from exc

    def dispatch(self, call: ToolCall) -> ToolResult:
        """Run the registered handler and wrap its outcome in a ToolResult.

        Why we catch broad `Exception`: FR-007 — a tool raising must surface
        as a structured `ToolResult(status="error", ...)`, never as an
        uncaught crash. We deliberately do NOT inspect the exception text to
        decide what to do next — `error_category` is filled from the
        exception's *type*, not its message.
        """
        # validate_call may raise MalformedToolUse — let it propagate so the
        # loop can label the termination cause precisely.
        self.validate_call(call)
        handler = self._handlers[call.tool_name]
        try:
            output = handler(call.input)
        except Exception as exc:  # noqa: BLE001 — see docstring rationale
            return ToolResult(
                tool_use_id=call.tool_use_id,
                status="error",
                output={"message": str(exc)},
                error_category=type(exc).__name__,
            )
        return ToolResult(
            tool_use_id=call.tool_use_id,
            status="ok",
            output=output,
            error_category=None,
        )


__all__ = ["MalformedToolUse", "ToolRegistry"]
