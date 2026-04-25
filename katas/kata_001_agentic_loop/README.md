# Kata 1 — Agentic Loop & Deterministic Control

> Constitution Principle I (Determinism Over Probability, NON-NEGOTIABLE)
> embodied as a working program: an agent loop whose every branching
> decision is the value of `stop_reason` — and nothing else.

## Objective (in my own words)

Build the smallest credible agent loop that drives Claude through a tool-using
session, where the only thing the loop is allowed to look at to decide what
to do next is the **structured `stop_reason` field** of each Messages-API
response. No regex over the assistant's prose. No `"task complete" in text`.
No "if the model said `done`, exit". The model's text is for the human to
read; the API's structured signals are for the program to follow.

## Architecture walkthrough

```
┌────────────────┐
│ runner.py CLI  │   →  picks LiveClient or RecordedClient via LIVE_API env var
└────────┬───────┘
         │
┌────────┴───────┐    ┌──────────────┐
│   loop.py      │───▶│  tools.py    │  (registry + dispatch — wraps errors)
│  (signal-only) │    └──────────────┘
└────────┬───────┘
         │
┌────────┴───────┐    ┌──────────────┐
│   events.py    │───▶│ runs/<id>/   │  (append-only JSONL audit)
└────────────────┘    │ events.jsonl │
                      └──────────────┘
```

- **`models.py`** — pydantic v2 schemas: `StopSignal` (Literal), `ToolCall`,
  `ToolResult`, `Turn`, `EventRecord`, `AgentSession`, plus `UnhandledStopSignal`
  for the values the loop refuses to recognize. Construction validates;
  invalid payloads raise (Principle II).
- **`client.py`** — thin `MessagesClient` Protocol with two implementations:
  `LiveClient` (real Anthropic SDK, lazy-imported) and `RecordedClient`
  (replays a fixture JSON). Tests inject the latter so the kata is offline-
  reproducible (SC-007).
- **`tools.py`** — `ToolRegistry` with duplicate-name rejection, JSON-Schema
  validation of tool inputs, and `dispatch()` that catches handler exceptions
  and wraps them in `ToolResult(status="error", ...)` (FR-007). Unknown tool
  or schema-invalid input raises `MalformedToolUse` (FR-008).
- **`events.py`** — `EventLog` writes one JSON line per loop iteration with
  stable key ordering and microsecond-precision UTC timestamps so two reruns
  diff byte-identical on the `stop_signal` + `branch_taken` columns (SC-007).
- **`session.py`** — `RuntimeSession` glues everything: `AgentSession` data,
  `ToolRegistry`, `EventLog`, and the in-memory `history` list.
- **`loop.py`** — `run()` is a switch on `stop_reason`. The function does
  not read `Turn.assistant_text_blocks`; an AST lint test fails the build if
  it ever does.
- **`replay.py`** — `reconstruct_trajectory(events_path)` returns the
  iteration count, tool-invocation count, termination cause, and the
  signal/branch column tuples — enough to rebuild the run trajectory from
  the log alone (SC-008).

## The anti-pattern this kata defends against

The lazy way to terminate a loop is to grep the model's prose:
`if "task complete" in response_text: break`. It works once. It breaks
silently the moment the model says "all done", "finished", "complete", or
swaps language. Worse, an attacker who can influence model output can
trigger early termination by saying the magic phrase.

This kata structurally forbids that path:

1. **Schema enforcement**: `EventRecord` uses pydantic `extra="forbid"`.
   No prose-derived field (`prose_excerpt`, `matched_phrase`, etc.) can be
   written to the event log — construction would raise.
2. **AST lint**: `tests/katas/kata_001_agentic_loop/lint/test_no_prose_matching.py`
   parses `loop.py` and fails the build on `import re`, on `.find` /
   `.search` / `.match` / `.startswith` / `.endswith` calls, and on the
   `in` operator against a string literal. A future contributor who adds
   "just one regex" cannot land it.
3. **Decoy-phrase fixture**: `decoy_phrase.json` injects every phrase from
   SC-004 into a `tool_use` turn's text body. The loop must keep going.
   A unit test parametrizes the same phrases for explicit coverage.

## Run instructions

```bash
# from repo root
pip install -e ".[dev]"

# Recorded fixtures (no API key needed) — default test path
pytest tests/katas/kata_001_agentic_loop -v

# Live API run
LIVE_API=1 ANTHROPIC_API_KEY=sk-... \
  python -m katas.kata_001_agentic_loop.runner \
  --model claude-opus-4-7 \
  --prompt "What is the weather in Bogotá?"
```

The runner prints a JSON summary to stdout including `session_id`,
`iterations`, `tool_invocations`, `termination_cause`, and the path to the
event log. Inspect it with:

```bash
jq -c '{iter: .iteration, signal: .stop_signal, branch: .branch_taken,
        tool: .tool_name, cause: .termination_cause}' \
  runs/<session-id>/events.jsonl
```

## Reproducibility

`runs/<session-id>/events.jsonl` is the **single source of truth** for what a
kata run did. Two independent runs against the same fixture produce
byte-identical `stop_signal` + `branch_taken` column sequences — verified by
`tests/katas/kata_001_agentic_loop/unit/test_trajectory_reconstruction.py::test_two_runs_have_byte_identical_signal_branch_columns`.

`replay.py::reconstruct_trajectory(events_path)` reads that file and returns
a `TrajectorySummary` (iterations, tool invocations, termination cause,
signal/branch tuples). No other source consulted.

## Reflection

- **Which prose phrase was most tempting to match on?** "task complete" — it
  *looks* like a structured signal. The mitigation isn't willpower; it's
  the AST lint. Even if I wanted to, the build won't let me ship a `re.search`
  against the assistant's prose.
- **Where would `re` sneak back in during maintenance?** The most likely
  vector is "we need to extract the city name from the tool result for
  logging" — innocent at first. The lint catches `import re`, but a
  resourceful contributor could write `text.split(' ')[0]`. So the
  defense-in-depth is `EventRecord(extra="forbid")`: even if some helper
  derives a string from prose, it cannot be persisted to the audit log.
  The log stays the source of truth, and the source of truth stays clean.
