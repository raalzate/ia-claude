# Specification Analysis Report — 014-few-shot-calibration

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B Ambiguity | MEDIUM | spec.md FR-001 "when measured zero-shot inconsistency on the edge-case corpus is ≥ 20%" | FR-001 ties the inclusion of examples to a measurement threshold (≥ 20% zero-shot inconsistency), but no task or feature ties the calibration runner to that precondition — calibration appears to run unconditionally in the harness. | Either enforce the 20% precondition in the runner (add a gate) and cite its task, or restate FR-001 as a recommendation without a hard conditional. |
| F-002 | G Inconsistency | MEDIUM | feature `calibrated_few_shot_vs_zero_shot.feature` Background says "a calibrated set of 3 input/output pairs"; spec.md US3 says "at least two distinct example sets of size 2–4"; tasks.md T017 records a "canonical 3-pair set" | Primary example-set size is 3 pairs in US1 fixture but the envelope is 2-4 for US3 rotation. Consistent, but the US3 scenario outline uses `calibrated_primary` and `calibrated_alternate` while tasks T043 records only `example_set_alternate.json` and T017 records only `example_set_calibrated.json` — the `calibrated_primary` / `calibrated_alternate` ids used in TS-009 examples are not wired to the fixture filenames. | Rename fixtures to match the scenario outline's `set_id` values or add an explicit mapping table in quickstart.md. |
| F-003 | C Underspec | MEDIUM | spec.md FR-002 "validate that the active example set covers representative edge cases for the task" | "Covers representative edge cases" is not machine-checkable — tasks.md T013 implements `validate_coverage(set_id, task_id)` but the predicate's contents (what counts as "covered") are not declared in FR-002 or the plan. | Declare the coverage predicate (e.g., "at least one pair per declared edge-case class in the task schema") in plan.md or research.md. |
| F-004 | H2 Traceability | MEDIUM | spec.md Edge Case "leakage (verbatim canonical input/output)" | plan+tasks treat leakage as a non-fatal flag (T011, T056, T063), but no BDD scenario covers the leakage flagger — edge case is described only in spec.md and plan.md. | Add a feature scenario for the leakage-candidate flagger or formally defer it via plan.md Complexity Tracking. |
| F-005 | G Inconsistency | LOW | tasks.md Phase 6 title "Example-Set Invariants & Contradiction Detection (US1 + US2 cross-cutting, Priority: P1)" vs feature tag `@US-001 @US-002` | Cross-cutting phase is explicitly documented; finding is informational. | No change required. |
| F-006 | B Ambiguity | LOW | spec.md SC-001 "≥ 40% (relative)" — "relative" modifier | SC-001 is explicit about relative vs absolute; tasks.md T029 enforces the "≥ 40% relative-reduction threshold" — aligned. | No change required. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | Calibration pass/fail keys on a numeric inconsistency delta; schema-validity is a typed boolean per output. |
| II. Schema-Enforced Boundaries | PASS | `ExamplePair`, `ExampleSet`, `FewShotPrompt`, `CalibrationReport`, `ConsistencyMetric` are pydantic v2; contracts under `contracts/`; `ExampleSet` 2-4 invariant and contradiction validator raise before API call. |
| III. Context Economy | PASS | `FewShotBuilder` emits `system_instructions + examples_block` as a stable prefix and `target_input` as the dynamic suffix (T025 asserts). |
| IV. Subagent Isolation | N/A | Single-agent calibration loop (plan.md declares). |
| V. Test-First Kata Delivery | PASS | Feature files locked with DO NOT MODIFY banner; contradictory-set fixture is explicitly red-first (tasks.md Notes). |
| VI. Human-in-the-Loop | PASS | FR-007 anti-pattern guard: zero-shot on flagged tasks halts without `acknowledge_zero_shot=True`. |
| VII. Provenance & Self-Audit | PASS | `runs/<session-id>/calibration.json` + `outputs.jsonl` stamp `example_set_id`, `corpus_id`, `model`; T070 Reproducibility section. |
| VIII. Mandatory Documentation | PASS | T064 README, T065 module docstrings, T066 why-comments, T067 example-selection contract doc. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Partial | T020, T021, T027, T028 | Yes | Summary — but the ≥20% conditional is not enforced by any task |
| FR-002 | Yes | T013, T049, T053 | Yes | Constraints, Constitution Check VI |
| FR-003 | Yes | T007, T012, T022, T027, T028, T047, T050 | Yes | Constraints |
| FR-004 | Yes | T021, T029, T035, T041, T048 | Yes | Summary |
| FR-005 | Yes | T010, T054, T060, T061, T062 | Yes | Constraints |
| FR-006 | Yes | T007, T058, T059, T062 | Yes | Constraints |
| FR-007 | Yes | T033, T034, T036, T037, T039, T040, T042 | Yes | Constraints, Constitution Check VI |
| SC-001 | Yes | T021, T029, T041, T048 | Yes | Summary |
| SC-002 | Yes | T023, T024, T030 | Yes | Constraints |
| SC-003 | Yes | T010, T054, T060, T061, T062 | Yes | Summary |
| SC-004 | Yes | T022, T027, T028, T047, T050 | Yes | Summary |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | None detected — tech (Python 3.11, pydantic v2, pytest-bdd, anthropic) lives in plan.md; spec.md stays implementation-neutral. | — |

## Metrics

- Total requirements: 11 (7 FR + 4 SC)
- Total tasks: 73
- Coverage: 100% (FR-001 conditional gate flagged F-001)
- Ambiguity count: 2
- Critical: 0 · High: 0 · Medium: 4 · Low: 2
- Total findings: 6

**Health Score**: 91/100 (stable — first run)

## Next Actions
- Resolve F-001 by either enforcing FR-001's 20% precondition in the runner or restating FR-001 as guidance.
- Resolve F-002 by renaming fixtures to match `calibrated_primary` / `calibrated_alternate` (or add a mapping table in quickstart.md).
- Declare the coverage predicate for FR-002 (F-003) so `validate_coverage` has a declared contract.
- Decide on BDD coverage for the leakage flagger (F-004) — add a scenario or formally defer.
