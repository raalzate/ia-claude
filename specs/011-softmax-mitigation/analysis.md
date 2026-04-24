# Specification Analysis Report — 011-softmax-mitigation

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | G2 prose range | MEDIUM | spec.md FR-002, SC-003 ("50–60% band") | FR-002 says fire "within the 50-60% band" but plan.md pins trigger at `>= 0.55` and BDD [TS-021] evaluates the trigger as `true` at 0.55, 0.59, 0.60, and 0.61 — the "band" is collapsed into a half-open `[0.55, ∞)` step function, not a band with an upper gate. | Clarify in spec.md whether 0.60 is still in-band or above-band; align language with the `[0.55, 0.60)` half-open interval used by CompactionEvent and the trigger step function. |
| F-002 | G Inconsistency | MEDIUM | tasks.md T052 `{0.49, 0.54, 0.55, 0.59, 0.60, 0.61}` vs feature TS-021 examples `{0.49, 0.55, 0.59, 0.60, 0.61}` | Unit boundary table adds 0.54 not present in BDD; harmless superset but the two boundary tables should be identical. | Make unit boundary table a superset explicitly or cite TS-021 verbatim. |
| F-003 | H2 Traceability | MEDIUM | FR-005 vs scenarios | FR-005 says System MUST reject "content or configuration that would push a declared critical rule out of an edge region or cause it to be buried in the middle" — BDD TS-004/TS-005 cover the evict-by-content and oversized-rule cases, but no scenario covers "configuration would bury a rule in the middle" (edit-time regression). | Add a scenario or explicitly defer edge case "Anti-pattern slips back in" to a later kata and note the deferral. |
| F-004 | C Underspec | MEDIUM | spec.md Edge case "Session reaches 100% before compaction fires" | Spec says system must "fail closed (refuse the turn or force compaction)" but the precise choice is unspecified; plan+tasks implement only "refuse" via `CompactionOverdue`. | Pin to one behavior (refuse via `CompactionOverdue`) in spec.md to match the plan. |
| F-005 | B Ambiguity | LOW | spec.md SC-001 "≥ 95%" across "the adversarial batch" | Batch size N is not fixed in spec; plan/tasks assume N=30. | Bind N (or a minimum N) into the spec to make SC-001 reproducible. |
| F-006 | D Phase sep | LOW | plan.md Summary mentions "fail-closed" and calls it "under Constitution v1.3.0 principles III ..." | Plan sentence drifts toward governance wording; acceptable since it cites, not defines. No action required. | No change required; informational. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | Numeric `usage_fraction` trigger; compliance scored via typed `compliance_probe_schema`; AST lint (T025) blocks prose matching. |
| II. Schema-Enforced Boundaries | PASS | `extra=forbid` on all pydantic models (T006); contract schemas under `contracts/`; TS-007/TS-014/TS-026/TS-027 validate serialized payloads. |
| III. Context Economy | PASS | Kata's raison d'être — edge-placement + 55% proactive compaction. |
| IV. Subagent Isolation | N/A | Single-agent kata per plan.md. |
| V. Test-First Kata Delivery | PASS | Feature files locked with DO NOT MODIFY banner; tasks.md notes "Verify every `.feature` scenario fails before writing the matching production code". |
| VI. Human-in-the-Loop | PASS | Reject-content gate (FR-005) halts with `EdgePlacementViolation`; `allow_anti_pattern` flag forces opt-in. |
| VII. Provenance & Self-Audit | PASS | `runs/kata-011/<session-id>/` persists layouts, `compliance.jsonl`, `compactions.jsonl`; T066 final self-audit. |
| VIII. Mandatory Documentation | PASS | T058 README, T059 module docstrings, T060 why-comments on every non-trivial site. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T022, T026, T027, T056 | Yes | Summary, Constraints, Constitution Check III |
| FR-002 | Yes | T007, T052, T054, T055 | Yes | Summary, Constraints |
| FR-003 | Yes | T007, T054, T056 | Yes | Constitution Check III |
| FR-004 | Yes | T011, T040 | Yes | Storage |
| FR-005 | Yes | T019, T024, T026 | Yes | Summary, Constitution Check VI |
| FR-006 | Yes | T034, T037, T039 | Yes | Constraints |
| FR-007 | Yes | T011, T028, T039, T053 | Yes | Storage, Constitution Check VII |
| SC-001 | Yes | T017, T049 | Yes | Summary, Technical Context (Testing) |
| SC-002 | Yes | T032 | Yes | Summary (anti-pattern report) |
| SC-003 | Yes | T044, T045, T052, T055 | Yes | Constraints |
| SC-004 | Yes | T047, T050, T054, T056 | Yes | Constraints |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | None detected — tech lives in plan.md (Python 3.11, pydantic v2, anthropic, tiktoken); spec.md stays implementation-free. | — |

## Metrics

- Total requirements: 11 (7 FR + 4 SC)
- Total tasks: 66
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 0 · Medium: 4 · Low: 2
- Total findings: 6

**Health Score**: 91/100 (stable — first run)

## Next Actions
- Resolve F-001 by aligning the "50–60% band" prose in spec.md FR-002/SC-003 with the half-open `[0.55, 0.60)` interval used by the trigger and `CompactionEvent` — single-word edits, no assertion change.
- Resolve F-004 by pinning the fail-closed choice on the "reaches 100% before compaction" edge case to "refuse turn via `CompactionOverdue`".
- Decide whether edge-time regression of the anti-pattern (F-003) is in scope; if yes add a scenario, if no cite the deferral in spec.md edge cases.
- Consider pinning the adversarial batch size N in SC-001 so the ≥95% rate is reproducible (F-005).
