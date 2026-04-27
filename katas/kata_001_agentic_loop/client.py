"""Thin injectable Anthropic client wrapper.

Why this seam exists:
    The kata's value is *deterministic* loop behaviour (Principle I). Hitting
    the real Messages API in tests would make the suite flaky and non-
    reproducible. We expose a single ``send(messages, tools) -> RawResponse``
    surface and provide two implementations: :class:`LiveClient` for runtime
    use, :class:`RecordedClient` for byte-deterministic test runs.

The wrapper deliberately returns a *plain dict* shaped exactly like the SDK
response (``stop_reason``, ``content`` blocks, ``id``). Loop logic parses
that dict — no SDK-specific objects leak past this module.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass
class RawResponse:
    """SDK-shaped response returned to the loop.

    Fields mirror the relevant slice of the Messages API:
        ``id``           — opaque response id, recorded for audit.
        ``stop_reason``  — the structural signal the loop branches on.
        ``content``      — list of blocks (``{"type": "text" | "tool_use", ...}``).
    """

    id: str
    stop_reason: str | None
    content: list[dict[str, Any]] = field(default_factory=list)


class AnthropicClient(Protocol):
    """Minimal interface the loop depends on (typed structural duck)."""

    def send(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> RawResponse:
        """Send one turn; return the SDK-shaped response."""


class RecordedClient:
    """Plays back a list of pre-recorded API responses.

    Why: each fixture file under ``tests/katas/kata_001_agentic_loop/fixtures/``
    is the recording of one full session. ``send`` returns the next response
    in sequence; running off the end raises so a misconfigured test fails
    loud instead of looping forever.
    """

    def __init__(self, recorded_turns: Iterable[dict[str, Any]]) -> None:
        """Capture the recorded turn sequence to play back on ``send``."""
        self._turns = list(recorded_turns)
        self._cursor = 0

    @classmethod
    def from_fixture(cls, path: str | Path) -> RecordedClient:
        """Build a client from a JSON fixture file (``{"turns": [...]}``)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        turns = data["turns"] if isinstance(data, dict) else data
        return cls(turns)

    def send(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> RawResponse:
        """Return the next recorded turn — ignores ``messages``/``tools``."""
        _ = messages, tools  # signal-driven loop ignores transcript here
        if self._cursor >= len(self._turns):
            raise RuntimeError("RecordedClient exhausted — fixture too short")
        turn = self._turns[self._cursor]
        self._cursor += 1
        return RawResponse(
            id=turn.get("id", f"rec-{self._cursor}"),
            stop_reason=turn.get("stop_reason"),
            content=list(turn.get("content", [])),
        )


class LiveClient:
    """Real Anthropic SDK client.

    Imported lazily so test runs do not require ``anthropic`` to be installed
    in some minimal CI lanes; instantiation fails loud if the key is missing,
    which is what we want — Principle I rejects silent fallbacks.
    """

    def __init__(self, model: str, max_tokens: int = 1024) -> None:
        """Construct the live client; refuses to start if the API key is missing."""
        try:
            import anthropic  # type: ignore  # noqa: PLC0415 — lazy import keeps SDK optional
        except ImportError as exc:  # pragma: no cover — depends on local env
            raise RuntimeError("anthropic SDK not installed") from exc
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY not set; refusing to LiveClient")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model
        self._max_tokens = max_tokens

    def send(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> RawResponse:
        """Forward to the real Messages API; reshape to :class:`RawResponse`."""
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            tools=tools,
            messages=messages,
        )
        # The SDK returns objects; normalise to plain dicts so downstream
        # parsing is identical to the recorded path.
        content_blocks: list[dict[str, Any]] = []
        for block in getattr(resp, "content", []) or []:
            block_type = getattr(block, "type", None)
            if block_type == "text":
                content_blocks.append({"type": "text", "text": getattr(block, "text", "")})
            elif block_type == "tool_use":
                content_blocks.append(
                    {
                        "type": "tool_use",
                        "id": getattr(block, "id", ""),
                        "name": getattr(block, "name", ""),
                        "input": getattr(block, "input", {}) or {},
                    }
                )
        return RawResponse(
            id=getattr(resp, "id", "live"),
            stop_reason=getattr(resp, "stop_reason", None),
            content=content_blocks,
        )
