# Specification Analysis Report — 004-subagent-isolation

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | Inconsistency | HIGH | plan.md §Source Code; tasks.md T001, T027 | Python package path `katas/004_subagent_isolation/` uses a leading digit in the submodule name. `python -m katas.004_subagent_isolation.runner` will fail. | Rename to `katas/kata_004_subagent_isolation/` across plan and tasks. |
| F-002 | Coverage / Ambiguity | MEDIUM | tasks.md T009 | T009 says "Copy JSON Schemas from `specs/004-subagent-isolation/contracts/` into a loader helper" but the plan assumes contracts exist (Phase 1 output of /iikit-02). No task verifies presence of the three schemas before use. | Add an explicit Phase-1 prereq check in tasks.md confirming `subtask-payload.schema.json`, `subagent-result.schema.json`, `handoff-contract.schema.json` are present. |
| F-003 | Ambiguity | MEDIUM | spec.md Edge Cases (Nested subagent spawning); plan.md; tasks.md T042 | Spec says a subagent may spawn further subagents; plan says subagents do NOT share the task-spawning tool "by default unless explicitly authorized". The authorization mechanism is described in task T042 but is not pinned in spec or plan (how a parent authorizes a child). | Document the authorization handshake (explicit allow-list on the nested subagent's tool list) in spec §Key Entities or plan §Constraints. |
| F-004 | Terminology | LOW | plan.md vs. tasks.md | Plan uses `TaskSpawner` Protocol; spec uses "task-spawning tool". Both are reconciled in the HandoffContract section but a reader switching between artifacts may conflate "protocol" with "tool". | Add a glossary line in spec or plan mapping "task-spawning tool" (spec) to `TaskSpawner` (plan implementation). |
| F-005 | Coverage | LOW | tasks.md T020 | FR-006 is exercised by T020 (default subagents exclude the task-spawning tool) and TS-005, but T020 tests only the default spawner. The "unless explicitly authorized" carve-out is not tested. | Add a unit test for the authorized-nested-spawn case exercising FR-006 + FR-007 together. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | ALIGNED | Subagent result acceptance is gated by pydantic validation (T054), not by reading prose. |
| II. Schema-Enforced Boundaries | ALIGNED | `SubtaskPayload`, `SubagentResult`, `HandoffContract` are pydantic v2 with `extra="forbid"` (T005); three JSON Schemas under `contracts/`. |
| III. Context Economy | ALIGNED | Not load-bearing; `SubtaskPayload` is minimal by construction. |
| IV. Subagent Isolation | ALIGNED | Core of the kata. AST lint (T037) + leak-probe UUID integration test (T038) + `extra="forbid"` triple defense. |
| V. Test-First Kata Delivery | ALIGNED | Gherkin locked; TS IDs cited per step-def task; tests precede implementation in each phase. |
| VI. Human-in-the-Loop | ALIGNED | Schema-validation failures raise terminal `SubagentResultValidationError` — reviewer is the escalation target. |
| VII. Provenance & Self-Audit | ALIGNED | Per-run JSONL files (T041) for `subagent_inputs.jsonl` and `subagent_outputs.jsonl`; auditor can diff against contracts. |
| VIII. Mandatory Documentation | ALIGNED | README (T059), docstrings (T060), why-comments (T061), contract doc (T062). |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T019, T024, T040 | Yes | Summary; Constitution Check II |
| FR-002 | Yes | T037, T043 | Yes | Constitution Check IV |
| FR-003 | Yes | T021, T054, T056 | Yes | Constitution Check I |
| FR-004 | Yes | T054, T058 | Yes | Constitution Check VI |
| FR-005 | Yes | T010, T041 | Yes | Constitution Check VII |
| FR-006 | Yes | T020 | Yes | Constitution Check IV |
| FR-007 | Yes | T039, T042 | Yes | Constitution Check IV |
| FR-008 | Yes | T053, T055, T057 | Yes | Summary |
| SC-001 | Yes | T037, T038 | Yes | Constraints |
| SC-002 | Yes | T054, T058 | Yes | Constraints |
| SC-003 | Yes | T053, T057 | Yes | Summary |
| SC-004 | Yes | T038 | Yes | Constraints |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| _n/a_ | _n/a_ | No violations detected. Spec stays narrative; plan holds tech (anthropic, pydantic); governance stays in CONSTITUTION.md. | _n/a_ |

## Metrics

- Total requirements: 12 (FR: 8, SC: 4)
- Total tasks: 67
- Coverage: 100%
- Ambiguity count: 1
- Critical: 0 · High: 1 · Medium: 2 · Low: 2
- Total findings: 5

**Health Score**: 90/100 (stable — first run)

## Next Actions

- Rename the `004_subagent_isolation` submodule to a Python-legal identifier across plan + tasks.
- Document the "explicitly authorized" nested-spawning handshake in `spec.md` or `plan.md`.
- Add a unit test covering FR-006 + FR-007 together (authorized nested spawn with a narrower allow-list).
- Add a prereq check that the three contract schemas are present before tasks consume them.
