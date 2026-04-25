"""Thin injectable Anthropic client wrapper for Kata 1.

Why this module exists at all (instead of calling `anthropic.Anthropic` from
the loop): plan.md D-004 — tests run offline against recorded fixtures so the
kata is reproducible (SC-007) and free of API-key requirements. The loop
depends only on the abstract `MessagesClient` protocol; tests inject
`RecordedClient`, production injects `LiveClient`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class RawResponse:
    """Minimal façade around an Anthropic Messages API response.

    Why we do not pass the SDK's response object straight through: the SDK
    returns a rich object whose surface evolves across versions. Locking the
    fields the loop reads to a small dataclass makes our contract explicit and
    keeps test fixtures decoupled from SDK internals.
    """

    response_id: str
    stop_reason: str | None
    content: list[dict[str, Any]]


class MessagesClient(Protocol):
    """Surface the loop depends on.

    Why a Protocol and not an ABC: structural subtyping lets test code pass
    plain objects (or even fixtures) without inheriting from a base class —
    keeping injection trivial.
    """

    def send(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> RawResponse:
        """Send messages to the model and return the structured response."""
        ...


class RecordedClient:
    """Replay a recorded session from a fixture JSON file.

    Why a list of pre-recorded responses (not a callable that simulates the
    API): SC-007 wants byte-identical reruns. Replaying a fixed sequence of
    responses guarantees the loop sees the same `stop_reason` values in the
    same order, regardless of clock or RNG.
    """

    def __init__(self, fixture_path: str | Path) -> None:
        """Eagerly load the recorded session at `fixture_path`."""
        path = Path(fixture_path)
        if not path.exists():
            raise FileNotFoundError(f"recorded fixture missing: {path}")
        # Why we eagerly load + index: a kata run is short. Streaming would
        # add complexity for no measurable win.
        data = json.loads(path.read_text())
        self._responses: list[dict[str, Any]] = list(data.get("responses", []))
        self._cursor: int = 0

    def send(
        self,
        *,
        model: str,  # noqa: ARG002 — kept for protocol parity
        messages: list[dict[str, Any]],  # noqa: ARG002
        tools: list[dict[str, Any]],  # noqa: ARG002
    ) -> RawResponse:
        """Return the next pre-recorded response from the fixture."""
        if self._cursor >= len(self._responses):
            raise RuntimeError("RecordedClient exhausted — fixture has no more recorded responses")
        record = self._responses[self._cursor]
        self._cursor += 1
        # Why we tolerate `stop_reason` being absent in the recording: FR-006
        # explicitly lists the absent-signal case as a halt condition the loop
        # must recognize. The fixture must be able to express it.
        return RawResponse(
            response_id=record.get("id", f"rec-{self._cursor:03d}"),
            stop_reason=record.get("stop_reason"),
            content=list(record.get("content", [])),
        )


class LiveClient:
    """Wrap the real `anthropic.Anthropic` client.

    Why we do not instantiate the SDK at module import: the SDK requires an
    API key, and importing the kata for tests must not require ANTHROPIC_API_KEY
    (per quickstart.md "default test run uses recorded fixtures").
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Lazily import and instantiate the official Anthropic SDK."""
        # Lazy import keeps the recorded-only path import-cheap.
        from anthropic import Anthropic  # noqa: PLC0415

        self._sdk = Anthropic(api_key=api_key) if api_key else Anthropic()

    def send(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> RawResponse:
        """Forward the call to `messages.create` and unwrap the response."""
        # Why max_tokens is required by the SDK but kept implicit here: the
        # loop is signal-driven; truncation surfaces as `stop_reason=max_tokens`
        # which the loop already handles (FR-006). 1024 is a workshop default.
        response = self._sdk.messages.create(
            model=model,
            max_tokens=1024,
            messages=messages,
            tools=tools or None,
        )
        # The SDK gives `content` as a list of block objects; we serialize via
        # `model_dump` so downstream code sees plain dicts identical in shape
        # to the fixture format.
        content_blocks = [
            block.model_dump() if hasattr(block, "model_dump") else dict(block)
            for block in response.content
        ]
        return RawResponse(
            response_id=response.id,
            stop_reason=response.stop_reason,
            content=content_blocks,
        )


__all__ = ["LiveClient", "MessagesClient", "RawResponse", "RecordedClient"]
