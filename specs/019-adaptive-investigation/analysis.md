# Specification Analysis Report — 019-adaptive-investigation

**Generated**: 2026-04-24T12:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B Ambiguity | HIGH | spec.md SC-002 ("target defined per evaluation cohort; minimum acceptable baseline is the rate agreed during kata calibration") | A primary measurable outcome leaves its threshold undefined — "target defined per evaluation cohort / agreed during calibration". No task or fixture pins a concrete percentage, so SC-002 cannot be falsified and the integration test T037 asserts behaviour qualitatively rather than against a numeric recall target. | Run `/iikit-clarify` on SC-002 to set a concrete percentage (e.g. ≥90% of seeded-surprise runs trigger a revision) before `/iikit-07-implement` so the assertion can be mechanised. |
| F-002 | C Underspec | MEDIUM | spec.md FR-004 ("time, iterations, or tool-call count"); plan.md §Constraints (`max_wall_seconds`, `max_revisions`) | Spec lists three possible budget dimensions; plan implements two (`max_wall_seconds`, `max_revisions`). Feature TS-015 only exercises these two. "Tool-call count" has no task or assertion. | Either explicitly drop tool-call-count from the spec or add a `max_tool_calls` budget predicate + test row (narrows scope to documented reality). |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | Planner branches on typed `TriggerEvent` + `stop_reason`; AST lint forbids `re`/`str.find`/`in`-against-str in `planner.py` (T019); `re` scoped to `topology_mapper.py` and justified under §Complexity Tracking + T020. |
| II. Schema-Enforced Boundaries | PASS | All pydantic models `extra="forbid"`; JSON Schemas Draft 2020-12 under `contracts/`; `PlanRevision.trigger` is non-null with enumerated `TriggerCategory` (T042). |
| III. Context Economy | PASS | Planner receives only validated `TopologyMap + Directive`; raw file contents never enter the prompt. |
| IV. Subagent Isolation | PASS | Hub-and-spoke (`Coordinator` hub, `TopologyMapper` + `Planner` spokes); typed handoffs; lint keeps `re` out of planner. |
| V. Test-First Kata Delivery | PASS | Four `.feature` files locked; tasks cite TS-IDs; hashes locked in context.json. |
| VI. Human-in-the-Loop | PASS | Directive contradiction emits `TriggerEvent(category="directive_contradiction")` and halts with a labeled escalation (T067). |
| VII. Provenance & Self-Audit | PASS | `plan-revisions.jsonl` append-only; every high-priority `PlanStep` carries `topology_refs` back-pointer (T026). |
| VIII. Mandatory Documentation | PASS | README + module docstrings + why-comments scheduled (T071–T074). |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T018, T021, T023, T025 | Yes | §Summary; §Constraints |
| FR-002 | Yes | T005, T019, T022 | Yes | §Summary |
| FR-003 | Yes | T036, T039, T040, T041, T068 | Yes | §Summary |
| FR-004 | Yes | T051, T053, T055 | Yes | §Summary |
| FR-005 | Yes | T010, T038, T042, T069 | Yes | §Summary |
| FR-006 | Yes | T052, T054, T056 | Yes | §Summary |
| FR-007 | Yes | T065, T067 | Yes | §Constitution Check |
| FR-008 | Yes | T022, T026 | Yes | §Summary |
| SC-001 | Yes | T022, T054, T079 | Yes | §Summary |
| SC-002 | Partial (qualitative) | T037, T079 | Yes | §Summary (target undefined) |
| SC-003 | Yes | T051, T055, T079 | Yes | §Summary |
| SC-004 | Yes | T038, T042, T079 | Yes | §Summary |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| _none_ | — | Tech (`pathlib`, `re`, `pydantic`, `anthropic`) confined to plan.md; spec.md is requirements-only; §Complexity Tracking correctly justifies the scoped `re` exception. | — |

## Metrics

- Total requirements: 12
- Total tasks: 79
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 1 · Medium: 1 · Low: 0
- Total findings: 2

**Health Score**: 93/100 (stable — first run)

## Next Actions
- Run `/iikit-clarify` on SC-002 to pin a concrete revision-trigger rate (e.g. ≥90% of injected-surprise runs) so the outcome is falsifiable.
- Either adopt a `max_tool_calls` budget predicate to match FR-004's third dimension, or narrow FR-004 to the two dimensions that plan/feature actually enforce.
