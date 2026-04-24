# Specification Analysis Report — 012-prompt-chaining

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | G2 prose range | MEDIUM | spec.md SC-001 "≥ 25%" vs plan.md "at least the declared coverage delta" vs tasks.md T029 "≥ 25 %" | SC-001's 25% threshold is hard-coded in spec+tasks but plan.md uses the vaguer phrase "declared coverage delta"; risk of drift if the threshold is ever tuned. | Make plan.md cite the 25% figure explicitly or treat SC-001 as the single source of truth and reference it by name. |
| F-002 | C Underspec | MEDIUM | spec.md Edge Cases — "very few files (1-2)" | Edge case is flagged but spec does not specify whether the chain still runs, bypasses, or warns when N≤2; tasks.md does not carry a test for this branch. | Either declare the small-N behavior in FR-00x and add a task/scenario, or explicitly defer it in edge cases. |
| F-003 | H2 Traceability | MEDIUM | spec.md "conflicting findings across per-file reports" edge case | No scenario/task explicitly covers cross-file conflicting findings during integration; implicitly covered by T022's duplicate-rejection validator but conflict surfacing is different from duplicate rejection. | Add an integration-stage scenario that asserts conflicting per-file findings surface rather than silently reconcile. |
| F-004 | G Inconsistency | LOW | tasks.md T009 exception `StageBudgetExceeded(stage_index, stage_name, declared_budget, measured_tokens, overflow)` vs feature TS-010 ("stage_index, stage_name, declared_budget, measured_tokens, and overflow fields") | Exact match — no gap. Kept as LOW informational. | No change required. |
| F-005 | B Ambiguity | LOW | spec.md FR-005 "without requiring modification of existing stage definitions, prompts, or payload contracts" | The diff check in tasks.md T038 covers `stages/per_file.py`, `stages/integration.py`, `stages/base.py` and earlier `output_schema` — does not mention prompt templates, which are inlined in the stage modules. | Confirm in plan/tasks that prompt templates living in the stage modules are covered by the byte-identity check or extract prompt templates to a dedicated file. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | Chain progression keys off pydantic-validated payloads; halts are typed exceptions, never string matches. |
| II. Schema-Enforced Boundaries | PASS | `extra="forbid"` on every entity (T007); `model_validate` at each stage boundary; contract schemas under `contracts/`. |
| III. Context Economy | PASS | Kata's raison d'être — per-file vs integration decomposition; `max_prompt_tokens` budget gate. |
| IV. Subagent Isolation | PASS | Plan explicitly models stage-to-stage as hub-and-spoke typed JSON payload; no inherited prompt context leaks downstream. |
| V. Test-First Kata Delivery | PASS | Feature files locked; tasks.md Phase order requires BDD failing before implementation. |
| VI. Human-in-the-Loop | PASS | `StageBudgetExceeded`, `MalformedIntermediatePayload`, `PerFileAnalysisHalt` halt the chain; human review surface is the escalation target. |
| VII. Provenance & Self-Audit | PASS | `runs/<task_id>/stage-<n>.json` is an append-only audit trail; FR-007 originating-stage tag on every artifact. |
| VIII. Mandatory Documentation | PASS | T045 README, T046 module docstrings, T047 why-comments, T048 payload-schema doc section. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T012, T021, T022, T023 | Yes | Summary, Constraints, Trace table |
| FR-002 | Yes | T012, T018, T044 | Yes | Trace table |
| FR-003 | Yes | T012, T021, T022, T033 | Yes | Constraints |
| FR-004 | Yes | T011, T012, T039, T044 | Yes | Constraints, Trace table |
| FR-005 | Yes | T002, T038, T041, T042 | Yes | Summary, Trace table |
| FR-006 | Yes | T007, T020, T023 | Yes | Trace table |
| FR-007 | Yes | T019, T022 | Yes | Constitution Check VII, Trace table |
| FR-008 | Yes | T021, T040, T043 | Yes | Constraints, Trace table |
| SC-001 | Yes | T029 | Yes | Summary, Trace table |
| SC-002 | Yes | T030, T033 | Yes | Summary, Trace table |
| SC-003 | Yes | T029, T030, T039, T040 | Yes | Summary, Trace table |
| SC-004 | Yes | T038, T041 | Yes | Summary, Trace table |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | None detected — tech (Python 3.11, pydantic v2, pytest-bdd, tiktoken) lives in plan.md; spec.md free of tech; governance lives in CONSTITUTION.md. | — |

## Metrics

- Total requirements: 12 (8 FR + 4 SC)
- Total tasks: 53
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 0 · Medium: 3 · Low: 2
- Total findings: 5

**Health Score**: 93/100 (stable — first run)

## Next Actions
- Resolve F-001 by citing the 25% figure explicitly in plan.md Trace table (or replacing "declared coverage delta" with the concrete number).
- Decide on small-N behavior (F-002): either add an FR for N≤2 with a corresponding task, or note the deferral in spec.md edge cases.
- Add a scenario for conflicting cross-file findings surfacing during the integration pass (F-003) so the "conflict surfacing" semantics are testable.
