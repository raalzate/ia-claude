# Implementation Plan: Strict Subagent Context Isolation (Hub-and-Spoke)

**Branch**: `004-subagent-isolation` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/004-subagent-isolation/spec.md`

## Summary

Build a hub-and-spoke Python kata under `katas/004_subagent_isolation/` where a
`Coordinator` owns the conversation history and delegates decomposable work to
one or more `Subagent` instances through a `TaskSpawner` dependency. Each
subagent runs in its own `anthropic.Anthropic().messages.create` session seeded
**only** from a pydantic `SubtaskPayload` constructed by the coordinator; the
subagent module has zero reference to the coordinator's private history
(enforced by an AST lint test). Subagent output is validated with pydantic
against a per-subtask `SubagentResult` model; malformed output is a terminal
error (FR-003, FR-004). A leak-probe test seeds a UUID into coordinator history
and asserts that no subagent input payload contains it (FR-001, FR-002, SC-001,
SC-004). A swap test replaces one concrete subagent with a stub and asserts
coordinator behavior is unaffected (FR-008, SC-003). Delivered under
Constitution v1.3.0 principles II (NN), IV, and VIII (NN).

## Technical Context

**Language/Version**: Python 3.11+ (matches Kata 1 baseline in
`specs/001-agentic-loop/plan.md`).
**Primary Dependencies**:
- `anthropic` — each `Subagent.run()` opens its own
  `anthropic.Anthropic().messages.create` call with the `SubtaskPayload` as the
  sole user-turn seed. The `Coordinator` uses the same SDK for its own
  messages but holds a disjoint `messages` list (FR-002, Principle IV).
- `pydantic` v2 — `SubtaskPayload`, `SubagentResult`, and
  `HandoffContract` are pydantic models; coordinator/subagent boundaries go
  through `model_validate_json` so invalid handoffs raise (FR-001, FR-003,
  Principle II NN).
- `pytest` + `pytest-bdd` — BDD runner consumes the Gherkin file produced by
  `/iikit-04-testify`.
**Storage**: Local filesystem only. Per-run artifacts written to
`runs/<session-id>/` (gitignored): `coordinator_history.json`,
`subagent_inputs.jsonl` (one line per spawned subagent — the exact
`SubtaskPayload` as serialized), `subagent_outputs.jsonl` (the exact raw
string returned and the validated `SubagentResult`). These feed the FR-005
audit diff and the SC-001 / SC-004 leak-probe check.
**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit + lint.
Fixture runs use a `RecordedSubagentClient` returning canned
`messages.create` responses (same VCR-style approach as Kata 1 D-004). Live
API runs are gated behind `LIVE_API=1`.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI — no server deployment.
**Project Type**: Single project. Kata lives at
`katas/004_subagent_isolation/`; tests at `tests/katas/004_subagent_isolation/`.
**Performance Goals**: Not latency-bound. Recorded-fixture acceptance suite
completes in under 5 seconds locally (same target as Kata 1).
**Constraints**:
- `katas/004_subagent_isolation/subagent.py` MUST NOT import, reference, or
  read any attribute on the coordinator's history (notably
  `Coordinator._history` or equivalent). This is enforced by
  `tests/katas/004_subagent_isolation/lint/test_no_history_leak.py`, an AST +
  grep test that fails the build on reintroduction (FR-002, Principle IV).
- Any subagent output that fails `SubagentResult.model_validate_json` surfaces
  as a `SubagentResultValidationError` and halts the coordinator's
  consumption of that result — no silent fallback, no best-effort coercion
  (FR-003, FR-004, SC-002).
- Leak-probe UUID seeded into coordinator history MUST appear **zero times**
  across the union of all `subagent_inputs.jsonl` lines for a given run
  (SC-001, SC-004).
**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test code;
one README; fixture corpus ≤ 8 recorded subagent sessions covering the happy
path, the leak-probe anti-pattern, malformed-output rejection, swap
equivalence, and nested-spawning recursion (edge case from spec).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Subagent result acceptance is gated by pydantic schema validation on `SubagentResult`, not by reading the subagent's prose. Coordinator never greps subagent text to decide success. |
| II. Schema-Enforced Boundaries (NN) | Every coordinator→subagent and subagent→coordinator boundary is a pydantic model (`SubtaskPayload`, `SubagentResult`). `additionalProperties: false` is set on both JSON schemas so extra fields cause rejection (spec Edge Case #2, FR-001). |
| III. Context Economy | Not load-bearing here — `SubtaskPayload` is minimal by construction, which coincidentally caps prompt size, but the kata's point is isolation, not cache retention. |
| IV. Subagent Isolation | Core of this kata. Coordinator and Subagent are separate classes in separate modules; subagent seeds its SDK call only from a `SubtaskPayload`; AST lint forbids any reference from the subagent module to coordinator private state (FR-002, FR-007, SC-001). |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code per Constitution v1.3.0 Development Workflow. Hashes will be locked in `.specify/context.json` before implement. |
| VI. Human-in-the-Loop | Schema-validation failures are terminal errors with a labeled reason (`SubagentResultValidationError`) rather than silent continuation, giving the human reviewer a clear escalation point. |
| VII. Provenance & Self-Audit | Per-run JSONL files (`subagent_inputs.jsonl`, `subagent_outputs.jsonl`) let an auditor diff declared schemas against actual payloads (FR-005). |
| VIII. Mandatory Documentation (NN) | Every non-trivial function (coordinator spawn path, subagent run, payload builder, validation gate) will carry a *why* comment tied to Principle IV or to the leak-probe anti-pattern. Feature ships a `README.md` (written during `/iikit-07-implement`) covering objective, walkthrough, anti-pattern defense, run instructions, and reflection. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/004-subagent-isolation/
  plan.md              # this file
  research.md          # Phase 0 output (decisions D-001..D-006 + Tessl note)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output — JSON Schema Draft 2020-12
    subtask-payload.schema.json
    subagent-result.schema.json
    handoff-contract.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # already present
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  004_subagent_isolation/
    __init__.py
    coordinator.py         # Coordinator: owns history, holds TaskSpawner dep
    subagent.py            # Subagent.run(): seeds SDK call from SubtaskPayload ONLY
    task_spawner.py        # protocol + default spawner; injection point for swap test
    models.py              # pydantic: SubtaskPayload, SubagentResult, HandoffContract
    client.py              # thin injectable Anthropic client wrapper (mirrors Kata 1 D-001)
    runner.py              # CLI: `python -m katas.004_subagent_isolation.runner`
    README.md              # kata narrative (written during /iikit-07)

tests/
  katas/
    004_subagent_isolation/
      conftest.py
      features/
        subagent_isolation.feature    # produced by /iikit-04-testify
      step_defs/
        test_subagent_isolation_steps.py
      unit/
        test_payload_minimization.py      # FR-001: only declared fields cross boundary
        test_result_validation.py         # FR-003, FR-004, SC-002
        test_swap_equivalence.py          # FR-008, SC-003 (stub subagent via TaskSpawner)
        test_nested_spawning.py           # FR-007: recursive isolation
      lint/
        test_no_history_leak.py           # AST/grep: subagent.py has no ref to Coordinator._history (FR-002, SC-001)
      integration/
        test_leak_probe.py                # SC-001, SC-004: UUID marker absent from all subagent inputs
      fixtures/
        happy_path.json                   # coordinator spawns 2 subagents, both return valid results
        leak_probe.json                   # coordinator history seeded with UUID; subagent inputs asserted clean
        malformed_result.json             # subagent returns non-conforming JSON -> terminal error
        swap_equivalent.json              # stub subagent honors same contract
        nested_spawn.json                 # subagent itself spawns a child; scoped payload only
```

**Structure Decision**: Single-project layout matching the Kata 1 convention
(see `specs/001-agentic-loop/plan.md` §Structure Decision). Coordinator and
Subagent live in **separate modules** so the AST lint
(`test_no_history_leak.py`) has a real module boundary to check. The
`task_spawner.py` module encapsulates the injection point that makes the P3
swap test (FR-008) a pure dependency swap with no coordinator change. Runs
written to `runs/<session-id>/` (gitignored) match Kata 1 provenance layout.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: retry budgets on subagent failure
(Edge Case #1 mandates terminal-error treatment, not retry), concurrent
subagent fan-out (acceptance scenarios are stated sequentially; concurrency
would obscure the leak-probe audit without adding pedagogical value), shared
utility library across katas (YAGNI per Kata 1 D-006 until a real duplicate
appears).
