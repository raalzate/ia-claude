"""Structured per-iteration event log shared by katas with control-flow demos.

The point is uniformity: every kata that draws a loop trace uses the same
shape of entries (dict with `iter`, `stop_reason`, `branch`, …) so that
the visual contrast between katas is immediate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Logger:
    """Append-only log of per-iteration entries."""

    entries: list[dict[str, Any]] = field(default_factory=list)

    def add(self, **fields: Any) -> None:
        """Record one event. Caller decides which fields are relevant."""
        self.entries.append(fields)

    def show(self) -> None:
        """Print one row per entry. Plain text so it survives notebook copy/paste."""
        if not self.entries:
            print("(log vacío)")
            return
        for e in self.entries:
            parts = [f"{k}={v}" for k, v in e.items()]
            print(" | ".join(parts))

    def __len__(self) -> int:
        return len(self.entries)
