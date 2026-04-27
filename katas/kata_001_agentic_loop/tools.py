"""Tool registry + dispatcher.

Why this module exists:
    The loop only knows *that* a tool was requested (via ``stop_reason="tool_use"``)
    and the structured ``ToolCall`` block. The registry is what turns that into
    an actual Python callable, validates the input against the tool's declared
    JSON schema (Principle II), and converts any raised exception into a
    :class:`~katas.kata_001_agentic_loop.models.ToolResult` with ``status="error"``
    so the loop continues under signal-driven rules (FR-007) — never via
    ``except: pass`` and never via inspecting response text.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema import exceptions as js_exc

from .models import ToolCall, ToolDefinition, ToolResult


class MalformedToolUse(Exception):
    """Raised when a ``tool_use`` block fails registry validation.

    Why a dedicated exception: FR-008 requires the loop to halt with a
    *labelled* termination reason on malformed tool use; the loop catches
    this exception specifically and emits ``termination_cause="malformed_tool_use"``.
    A bare ``ValueError`` would be ambiguous with model-validation errors.
    """


# A tool implementation is any callable that takes the validated input dict
# and returns a JSON-serialisable result. Returning anything serialisable is
# fine; raising is fine too — the dispatcher captures both.
ToolImpl = Callable[[dict[str, Any]], Any]


class ToolRegistry:
    """Hold tool definitions + their implementations.

    Public surface:
        - :meth:`register`     — add one tool; rejects duplicate names.
        - :meth:`as_sdk_tools` — return the list shape the SDK expects.
        - :meth:`dispatch`     — run a :class:`ToolCall` and return a
          :class:`ToolResult` (never raises for routine tool errors).
    """

    def __init__(self) -> None:
        """Start with an empty registry — tools are added via :meth:`register`."""
        self._defs: dict[str, ToolDefinition] = {}
        self._impls: dict[str, ToolImpl] = {}

    def register(self, definition: ToolDefinition, impl: ToolImpl) -> None:
        """Register a single tool. Duplicate names raise ``ValueError``."""
        if definition.name in self._defs:
            raise ValueError(f"duplicate tool registration: {definition.name}")
        self._defs[definition.name] = definition
        self._impls[definition.name] = impl

    @property
    def definitions(self) -> list[ToolDefinition]:
        """All registered definitions, in registration order."""
        return list(self._defs.values())

    def as_sdk_tools(self) -> list[dict[str, Any]]:
        """Shape the registry as the SDK ``tools=...`` parameter expects."""
        return [
            {
                "name": d.name,
                "description": d.description,
                "input_schema": d.input_schema,
            }
            for d in self._defs.values()
        ]

    def validate_call(self, call: ToolCall) -> None:
        """Pre-dispatch validation. Raises :class:`MalformedToolUse` on failure.

        Why split from ``dispatch``: the loop needs the malformed-tool-use
        check to halt the loop *before* any side effect happens. Routine
        tool *execution* errors are different — they are recovered via
        :meth:`dispatch` returning ``ToolResult(status="error")``.
        """
        if call.tool_name not in self._defs:
            raise MalformedToolUse(f"unknown tool: {call.tool_name}")
        schema = self._defs[call.tool_name].input_schema
        try:
            Draft202012Validator(schema).validate(call.input)
        except js_exc.ValidationError as exc:
            raise MalformedToolUse(f"invalid input for {call.tool_name}: {exc.message}") from exc

    def dispatch(self, call: ToolCall) -> ToolResult:
        """Validate + run a tool. Routine errors return ``status='error'``.

        Critically, this method NEVER reads ``call.input`` text or any
        assistant-text block to make a decision (FR-007 + Principle I). It
        consults the registered implementation and the JSON schema only.
        """
        # validate_call is the only place that may raise MalformedToolUse;
        # the loop catches that to emit a labelled termination.
        self.validate_call(call)
        impl = self._impls[call.tool_name]
        try:
            output = impl(call.input)
        except Exception as exc:  # noqa: BLE001 — by design: capture all.
            # Why catch broadly: the kata is about *signal-driven control*.
            # Any tool exception is mechanically converted to a structured
            # error so the loop can continue without consulting prose.
            return ToolResult(
                tool_use_id=call.tool_use_id,
                status="error",
                output=str(exc),
                error_category=type(exc).__name__,
            )
        return ToolResult(
            tool_use_id=call.tool_use_id,
            status="ok",
            output=output,
            error_category=None,
        )
