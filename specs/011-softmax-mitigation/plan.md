# Implementation Plan: Softmax Dilution Mitigation

**Branch**: `011-softmax-mitigation` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/011-softmax-mitigation/spec.md`

## Summary

Build a Python kata module that protects hard, non-negotiable business rules
from the U-shaped "lost in the middle" attention failure mode of transformer
LLMs. A `PromptBuilder` renders three comparable layouts — edge-placed,
mid-buried, and edge-placed + proactive compaction — against an adversarial
filler corpus. A compliance harness executes N trials per layout against the
live `anthropic` Messages API and records per-trial rule-obedience as a binary
outcome. A `CompactionTrigger` fires when `total_tokens / context_window ≥ 0.55`
and re-anchors every declared critical rule verbatim at both edges before the
next turn. Multi-rule competition for edge budget is resolved by a declared
priority integer with input-order tie-break. Content whose inclusion would
evict a critical rule from its edge region is rejected with a structured,
auditable exception (FR-005). Delivered under Constitution v1.3.0 principles
III (Context Economy — load-bearing for this kata), II (Schema-Enforced
Boundaries), V (TDD), VII (Self-Audit), VIII (Mandatory Documentation).

Tech choices trace to requirements:

- Python 3.11 + `pydantic` v2 (schemas per-entity) → FR-001, FR-003, FR-004,
  FR-005, FR-007, Principle II.
- `anthropic` SDK for live compliance measurement → SC-001, SC-002, US1-AS1,
  US2-AS1, US3-AS3.
- `pytest` + `pytest-bdd` for BDD acceptance + unit for the builder / trigger
  → Principle V, every FR and SC.
- Offline fixtures + `LIVE_API=1` gate for compliance runs → US1 Independent
  Test, US2 Independent Test, US3 Independent Test; keeps CI quota-free.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — sole transport for the compliance
  measurements needed to produce SC-001 and SC-002 on the practitioner's own
  workload.
- `pydantic` v2 — schema enforcement for `CriticalRule`, `EdgeRegion`,
  `PromptLayout`, `CompactionEvent`, `ComplianceRecord` (Principle II).
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).
- `tiktoken` (or an equivalent offline tokenizer) — deterministic token
  counting for `length_tokens`, edge-budget enforcement, and the 55% capacity
  trigger. Live API token counts are used for cross-checks only, never for
  dispatching the trigger (Principle I — signal-driven).

**Storage**: Local filesystem only. Per-run artifacts under
`runs/kata-011/<session-id>/`:
- `layouts/<label>.txt` — the exact rendered prompt per layout for audit.
- `compliance.jsonl` — one `ComplianceRecord` per trial (JSONL, append-only).
- `compactions.jsonl` — one `CompactionEvent` per compaction (JSONL,
  append-only) — feeds SC-003 and SC-004 verification.

**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit. Default
test run is offline against recorded `anthropic` fixtures under
`tests/katas/011_softmax_mitigation/fixtures/`. A live compliance sweep is
gated by `LIVE_API=1` and runs only on explicit opt-in so CI stays deterministic
and quota-free.

**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions CI
(Linux). Live sweep runs locally or in a separately-scheduled CI job that
carries an `ANTHROPIC_API_KEY` secret.

**Project Type**: Single project — one kata module under
`katas/011_softmax_mitigation/` with its own tests alongside, matching the
pattern established by kata 001.

**Performance Goals**: Not latency-bound. Offline acceptance runs complete
under 5 seconds. A live compliance sweep with N=30 trials × 3 layouts completes
inside the API's default rate limits; the harness surfaces per-trial duration
in `ComplianceRecord.latency_ms` for audit but asserts no p95 target — the
kata's goal is compliance rate, not speed.

**Constraints**:
- `PromptLayout` rendering MUST place every declared `CriticalRule` at both
  the primacy and latency edges for the `edge_placed` and
  `edge_placed_with_compaction` layouts (FR-001, FR-003) — enforced by
  pydantic model validators, not by hoping the caller got it right.
- `CompactionTrigger` MUST fire before `usage_fraction > 0.60` (FR-002, SC-003)
  — unit-tested by feeding the trigger synthetic token counts at 0.49, 0.55,
  0.59, 0.60, and 0.61 and asserting the fire/no-fire decision on each.
- The `mid_buried` layout is the labelled anti-pattern (US2); FR-006 requires
  an explicit `allow_anti_pattern=True` opt-in flag on the builder to render
  it, otherwise construction raises. Production callers never pass the flag.
- No regex-over-prose is used to judge rule compliance. Compliance is scored
  by a typed `ComplianceOutcome` payload — either the model emits a structured
  JSON response conforming to the rule's `compliance_probe_schema`, or the
  trial is counted as `undetermined` and surfaced rather than silently
  discarded (Principle I).

**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test code;
one `README.md` (Phase VIII); fixture corpus covering the three layouts on
two critical-rule shapes (short, boundary-sized) plus the five edge cases
enumerated in `spec.md`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | The `CompactionTrigger` fires on a numeric token-usage fraction, never on model prose. Compliance scoring consumes a typed `ComplianceOutcome` payload (structured JSON from the model against a declared probe schema) — text-search over the response body is forbidden in scoring logic and will be caught by the per-kata AST-lint pattern carried forward from kata 001. |
| II. Schema-Enforced Boundaries (NN) | Every entity — `CriticalRule`, `EdgeRegion`, `PromptLayout`, `CompactionEvent`, `ComplianceRecord` — is a pydantic v2 model with JSON Schema exports under `contracts/` (`$id` prefix `https://ia-claude.local/schemas/kata-011/...`). Invalid payloads raise `ValidationError` and abort the run. |
| III. Context Economy (load-bearing) | This kata *is* the Principle III kata. Edge placement, multi-rule priority, reject-content gate, and the 55% proactive compaction threshold operationalise the principle as executable code and BDD assertions. |
| IV. Subagent Isolation | Not applicable — single-agent kata. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` will lock `.feature` files and assertion-integrity hashes before any production code. `tasks.md` (generated later by `/iikit-05-tasks`) will reference test IDs. This plan does NOT commit code. |
| VI. Human-in-the-Loop Escalation | The reject-content gate (FR-005) halts composition with a typed exception rather than silently reordering the prompt — the human author is the escalation target. The `allow_anti_pattern` flag forces explicit opt-in to render the US2 mid-buried layout. |
| VII. Provenance & Self-Audit | `runs/kata-011/<session-id>/` persists every rendered layout, every compaction event, and every compliance trial with its trial id, rule id, layout label, model id, and outcome — sufficient to re-derive SC-001, SC-002, SC-003, SC-004 from the files alone. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function / validator will carry a *why* comment tied to the FR or the anti-pattern it defends against. Kata `README.md` (produced during `/iikit-07-implement`) will cover objective, walkthrough, anti-pattern defense, run instructions, and reflection. |

**Result:** PASS. Proceed to Phase 0 / 1 artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/011-softmax-mitigation/
  plan.md              # this file
  research.md          # Phase 0 — decisions D-001..D-007 + Tessl discovery
  data-model.md        # Phase 1 — CriticalRule, EdgeRegion, PromptLayout, CompactionEvent, ComplianceRecord
  quickstart.md        # Phase 1 — install, fixture run, LIVE_API run, scenario→spec map, §Kata Completion checklist
  contracts/           # Phase 1 — JSON Schemas (one per entity, $id kata-011)
    critical-rule.schema.json
    prompt-layout.schema.json
    compaction-event.schema.json
    compliance-record.schema.json
  checklists/
    requirements.md    # (already present — produced by /iikit-01)
  tasks.md             # (generated later by /iikit-05-tasks)
  README.md            # Principle VIII deliverable — written during /iikit-07
```

### Source Code (repository root)

```text
katas/
  011_softmax_mitigation/
    __init__.py
    models.py              # pydantic v2: CriticalRule, EdgeRegion, PromptLayout, CompactionEvent, ComplianceRecord
    prompt_builder.py      # PromptBuilder: emits edge_placed / mid_buried / edge_placed_with_compaction layouts
    compaction.py          # CompactionTrigger: fires at ≥0.55, re-anchors rules verbatim at edges
    compliance.py          # Compliance harness: N trials × L layouts → ComplianceRecord rows
    client.py              # Thin injectable Anthropic client wrapper (shared shape with kata 001)
    runner.py              # CLI entrypoint: `python -m katas.011_softmax_mitigation.runner`
    README.md              # kata narrative — written during /iikit-07

tests/
  katas/
    011_softmax_mitigation/
      conftest.py          # fixture loader, tokenizer fixture, RecordedClient
      features/            # Gherkin files produced by /iikit-04-testify
        softmax_mitigation.feature
      step_defs/
        test_softmax_mitigation_steps.py
      unit/
        test_prompt_builder_edges.py         # FR-001, FR-003, FR-005
        test_compaction_trigger_threshold.py # FR-002, SC-003 — boundary table
        test_rule_priority_competition.py    # edge-case: multi-rule competition
        test_reject_content_gate.py          # FR-005
        test_anti_pattern_flag.py            # FR-006
        test_compliance_record_shape.py      # FR-007, schema conformance
      lint/
        test_no_prose_matching.py            # AST check carried from kata 001 — scoring MUST be signal-driven
      fixtures/
        edge_placed_short.json               # recorded Anthropic response, structured compliance probe
        edge_placed_boundary.json
        mid_buried_short.json
        compaction_event_boundary.json
        rule_evicts_content.json
        multi_rule_priority.json
```

**Structure Decision**: Single-project layout, mirroring kata 001. Kata 011
owns its own `PromptBuilder` and `CompactionTrigger`; a future refactor may
extract a shared `PromptComposer` after kata 010 (prefix caching) implements
the adjacent concept, but no shared module is introduced now. That avoids
premature coupling and matches the FDD "vertical delivery per kata" rule in
Constitution §Development Workflow. Live runs write to
`runs/kata-011/<session-id>/` (gitignored).

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│   Prompt Builder   │───────│ Compaction Trigger │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Messages API  │ │ Compliance Log │ │ Rules Registry │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `Prompt Builder` owns the core control flow
for this kata's objective; `Compaction Trigger` is the primary collaborator/policy reference;
`Messages API`, `Compliance Log`, and `Rules Registry` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally deferred: a cross-kata `PromptComposer` shared
between katas 010 and 011 (revisit after kata 010 implement lands), a
GPU-accurate tokenizer (the kata's thresholds are coarse — `tiktoken` or the
SDK's `count_tokens` helper is sufficient), and an async batch harness for the
compliance sweep (the default N=30 × 3 layouts sits well inside live rate
limits; batch mode can be layered later per Constitution §Development Workflow
"asynchronous batch processing when results are not user-blocking").
