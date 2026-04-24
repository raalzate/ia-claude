# Implementation Plan: Agentic Loop & Deterministic Control

**Branch**: `001-agentic-loop` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/001-agentic-loop/spec.md`

## Summary

Build a minimal, auditable Python kata module that drives a Claude agent loop
**exclusively** from the structured `stop_reason` field of the Messages API
response. The loop dispatches tools on `tool_use`, appends tool results, halts
on `end_turn`, and halts explicitly on any unhandled signal — never inspecting
response prose. Every iteration emits a JSONL event-log record sufficient to
reconstruct the loop's trajectory offline. Delivered under Constitution v1.2.0
principles I (Determinism), II (Schema-Enforced Boundaries), V (TDD), VII
(Self-Audit), VIII (Mandatory Documentation).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — sole source of `stop_reason` signals.
- `pydantic` v2 — schema enforcement for tool definitions, tool results, and
  event-log records (Principle II).
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).
**Storage**: Local filesystem only. Event log written as append-only JSONL
(`runs/<session-id>/events.jsonl`). Conversation history held in memory for the
duration of a session; optionally mirrored to `runs/<session-id>/history.json`
for replay.
**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit tests. Fixture sessions for the Messages API are recorded once (VCR-style
JSON fixtures under `tests/fixtures/`) so tests run offline and deterministically.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions CI
(Linux). No server deployment.
**Project Type**: Single project — one kata module under `katas/kata_001_agentic_loop/`
with its own tests alongside.
**Performance Goals**: Not latency-bound. Acceptance runs against recorded
fixtures complete in under 5 seconds locally.
**Constraints**:
- Event-log JSONL records MUST be schema-valid or the run fails loud.
- Absolutely no `re`, `str.find`, `in` operator, `.startswith(`, `.endswith(`,
  nor string `==` / equality comparison against response text, or equivalent
  text search over `response.content` text blocks is permitted in termination
  logic — enforced by a lint step (see `tests/lint/no_prose_matching_test.py`).
  Scope of the gate: the AST lint walks `katas/kata_001_agentic_loop/loop.py`
  and fails on any of these operators applied to assistant-text blocks; it is
  deliberately broader than FR-004's minimum so regressions fail loudly.
- All network calls live behind a thin injectable client so tests can swap a
  recorded-response client for the real SDK.
**Scale/Scope**: One kata, ~300–500 LOC implementation + comparable test code;
one README; fixture corpus ≤ 10 recorded sessions covering the happy path, the
anti-pattern defense, and every declared edge case.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Loop branches solely on `stop_reason`. A dedicated lint test fails the build if source imports `re` inside the loop module. |
| II. Schema-Enforced Boundaries (NN) | All tool payloads, tool results, and event-log records are pydantic models. Invalid records raise — never best-effort parsed. |
| III. Context Economy | Not load-bearing for this kata (it isn't a context-engineering kata) — plan keeps runtime logging terse to avoid token bloat when tools return large payloads. |
| IV. Subagent Isolation | Not applicable here — this kata runs a single agent. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` will be run before any production code per Constitution; `tasks.md` will be generated from the Gherkin features produced by testify. |
| VI. Human-in-the-Loop | The unhandled-signal branch halts with a labeled reason instead of silently continuing — the human reviewing the log is the escalation target. |
| VII. Provenance & Self-Audit | Event log is append-only JSONL with iteration index, signal, branch, tool name, termination cause — sufficient to reproduce the trajectory. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function will carry a *why* comment tied to the kata objective; this feature ships a `README.md` with objective, walkthrough, anti-pattern defense, run instructions, and reflection (written during `/iikit-07-implement`). |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/001-agentic-loop/
  plan.md              # this file
  research.md          # Phase 0 output (decisions + Tessl discovery notes)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output (tool + event-log JSON schemas)
    tool-definition.schema.json
    tool-result.schema.json
    event-log-record.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  kata_001_agentic_loop/
    __init__.py
    loop.py              # agentic loop (branches on stop_reason only)
    client.py            # thin injectable Anthropic client wrapper
    tools.py             # tool registry + pydantic schemas for tool calls
    events.py            # EventLog writer (append-only JSONL)
    models.py            # pydantic models: Turn, StopSignal, ToolInvocation, EventRecord
    runner.py            # CLI entrypoint: `python -m katas.kata_001_agentic_loop.runner`
    README.md            # kata narrative (written during /iikit-07)

tests/
  katas/
    kata_001_agentic_loop/
      conftest.py        # fixture session loader, event-log assertions
      features/          # Gherkin files produced by /iikit-04-testify
        agentic_loop.feature
      step_defs/
        test_agentic_loop_steps.py
      unit/
        test_loop_branches.py
        test_event_log_shape.py
      lint/
        test_no_prose_matching.py   # AST check: loop.py MUST NOT import re / call .find / use `in` on str
      fixtures/
        happy_path.json            # recorded session: tool_use → end_turn
        decoy_phrase.json          # decoy "task complete" in prose, non-terminal signal
        max_tokens.json            # max_tokens stop reason
        malformed_tool_use.json    # missing required tool_use fields
        unknown_signal.json
        absent_signal.json
```

**Structure Decision**: Single-project layout. Each kata is a first-class
package under `katas/kata_NNN_<slug>/`; tests mirror that structure under
`tests/katas/kata_NNN_<slug>/`. Runs are written to `runs/<session-id>/` (gitignored).
This keeps the 20 katas independently buildable and testable without cross-kata
coupling — matching FDD delivery cadence.

## Architecture

```
┌────────────────────┐
│ Practitioner CLI   │
└─────────┬──────────┘
          │
┌─────────┴──────────┐       ┌────────────────────┐
│   Agentic Loop     │───────│   Tool Registry    │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌─────────┴────────┐ ┌──┴───────────────┐ ┌───┴──────────────────┐
│ Event Log (JSONL)│ │ Recorded Fixtures│ │Anthropic Messages API│
└──────────────────┘ └──────────────────┘ └──────────────────────┘
```

Node roles: `Practitioner CLI` drives a session; the `Agentic Loop` is the
single decision point and branches solely on `stop_reason`; the `Tool Registry`
holds the declared tool schemas and is consulted synchronously per turn; the
`Event Log (JSONL)` captures every iteration for replay; `Recorded Fixtures`
stand in for `Anthropic Messages API` during offline test runs.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: retries, exponential backoff, concurrent
tool dispatch, persistent DB — none are required by the spec or by the
constitution, and Principle "don't add surrounding cleanup" (per project AGENTS)
blocks them.
