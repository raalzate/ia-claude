"""Reconstruct loop trajectory from a JSONL event log.

Why this lives next to the loop instead of in tests: SC-008 wants a reviewer
to reconstruct iterations / tool invocations / termination cause from the log
alone in under five minutes. Shipping the helper alongside the kata makes that
self-evident — the README points at this function as the canonical reader.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrajectorySummary:
    """The bare facts a reviewer needs from a log file.

    Why a frozen dataclass and not a pydantic model: the input is already
    schema-validated by the writer; this struct exists only as a return-type
    contract for `reconstruct_trajectory`.
    """

    iterations: int
    tool_invocations: int
    termination_cause: str | None
    stop_signals: tuple[str, ...]
    branches: tuple[str, ...]


def reconstruct_trajectory(events_path: str | Path) -> TrajectorySummary:
    """Parse a JSONL event log and return its observable trajectory.

    Why we expose `stop_signals` and `branches` as tuples: SC-007 (byte-
    identical reruns) is checked by diffing exactly these two columns across
    runs. Returning them as a stable, hashable shape makes that diff trivial.
    """
    path = Path(events_path)
    iterations = 0
    tool_invocations = 0
    termination_cause: str | None = None
    stop_signals: list[str] = []
    branches: list[str] = []

    for line in path.read_text().splitlines():
        if not line:
            continue
        record = json.loads(line)
        iterations = max(iterations, record["iteration"] + 1)
        if record["branch_taken"] == "tool_dispatch":
            tool_invocations += 1
        if record.get("termination_cause"):
            # The schema guarantees at most one populated termination_cause.
            termination_cause = record["termination_cause"]
        stop_signals.append(record["stop_signal"])
        branches.append(record["branch_taken"])

    return TrajectorySummary(
        iterations=iterations,
        tool_invocations=tool_invocations,
        termination_cause=termination_cause,
        stop_signals=tuple(stop_signals),
        branches=tuple(branches),
    )


__all__ = ["TrajectorySummary", "reconstruct_trajectory"]
