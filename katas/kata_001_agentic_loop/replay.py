"""Trajectory reconstruction from the event log alone.

Why this exists:
    Constitution Principle VII (Provenance & Self-Audit) and SC-008 require
    that a reviewer be able to identify iteration count, tool invocations,
    and termination cause without consulting the model's text or the
    in-memory state. ``reconstruct_trajectory`` parses ``events.jsonl`` and
    returns those three numbers — proving the log is sufficient.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrajectorySummary:
    """Summary fields a reviewer can compute from the log alone (SC-008)."""

    iterations: int
    tool_invocations: int
    termination_cause: str | None


def reconstruct_trajectory(events_path: str | Path) -> TrajectorySummary:
    """Read a JSONL event log and compute the summary triple.

    Why a frozen dataclass: comparison semantics are exact equality, which
    is what the SC-007 byte-identical-diff test relies on.
    """
    path = Path(events_path)
    iterations = 0
    tool_invocations = 0
    termination_cause: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        iterations += 1
        if record.get("branch_taken") == "tool_dispatch":
            tool_invocations += 1
        if record.get("termination_cause"):
            termination_cause = record["termination_cause"]
    return TrajectorySummary(
        iterations=iterations,
        tool_invocations=tool_invocations,
        termination_cause=termination_cause,
    )
