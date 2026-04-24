# Specification Analysis Report — 015-self-correction

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B Ambiguity | MEDIUM | spec.md SC-001 "greater than or equal to the target threshold on the labeled test set" | SC-001's target threshold is not numeric — it reads "target threshold" without a concrete value; tasks.md does not bind a number either. | Pin a numeric threshold (e.g., ≥ 95% true-positive AND ≥ 95% true-negative) in spec.md or move SC-001 to a manually-verified criterion with explicit acknowledgement. |
| F-002 | C Underspec | MEDIUM | spec.md FR-008 "System MUST declare and persist the tolerance value" + feature TS-002 "tolerance persisted" | Tolerance semantics — units (cents vs percent), single vs per-currency — are specified only in plan.md (`tolerance_cents: int = 1`). Spec.md omits the unit. | Add unit ("cents", integer) and default value to FR-008 in spec.md. |
| F-003 | H2 Traceability | MEDIUM | spec.md Edge "Non-numeric amounts" — examples `"TBD"`, `"see attached"` | Covered by TS-011 Scenario Outline and tasks.md T038, but spec.md FR-009 phrases this as "any extraction that cannot populate both totals MUST be flagged as a conflict rather than returned with null coerced to zero" — broader than the two example tokens. The scenario covers two tokens, not the general "cannot populate both totals" predicate. | Widen TS-011's defect class or add a scenario covering "structurally unparseable row" beyond literal-string defects. |
| F-004 | G Inconsistency | LOW | plan.md `conflict_detected` derivation `abs(stated_total - calculated_total) > tolerance_cents/100` vs spec.md FR-004 "declared, documented tolerance" | Consistent — plan gives the precise formula; spec keeps it abstract. | No change required; informational. |
| F-005 | B Ambiguity | LOW | spec.md Edge "Currency mismatches" — "A conflict must be detected rather than coerced" | Scenario TS-011 covers "different currency" and "mixed currencies" as `defect` cases and asserts `conflict_detected=true`; alignment is clean. | No change required. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | `conflict_detected` is computed from `abs(stated_total - calculated_total)` (Decimal) vs `tolerance_cents/100`; no prose involved. |
| II. Schema-Enforced Boundaries | PASS | `LineItem`, `InvoiceExtraction`, `ConflictRecord`, `ReviewQueueEntry`, `CalculationTrace` are pydantic v2; `model_validator(mode="after")` forgery gate (T009); JSON Schema contracts under `contracts/`. |
| III. Context Economy | N/A | Plan: "Not load-bearing here". Calculation trace is structured not prose. |
| IV. Subagent Isolation | N/A | Single extraction pass per invoice. |
| V. Test-First Kata Delivery | PASS | Feature files locked with DO NOT MODIFY banner; T041/T042 lint tests are irreversible guardrails. |
| VI. Human-in-the-Loop | PASS | Review queue IS the escalation target; every conflict routes to `review-queue.jsonl`; no conflict auto-resolved. |
| VII. Provenance & Self-Audit | PASS | Dual-total emission; `CalculationTrace` on every extraction (FR-007); `source_page_ref` on line items; `extractions.jsonl` + `review-queue.jsonl` append-only. |
| VIII. Mandatory Documentation | PASS | T053 README with objective+loop+anti-pattern+run+reflection; T054 retry-budget note; T055 module docstrings; T056 why-comments. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T008, T020, T023, T026, T044, T046 | Yes | Summary, Constraints |
| FR-002 | Yes | T009, T017, T021, T027, T051 | Yes | Summary |
| FR-003 | Yes | T008, T009, T026, T030, T039, T047 | Yes | Constraints |
| FR-004 | Yes | T009, T017, T024, T030, T047 | Yes | Constraints |
| FR-005 | Yes | T011, T031, T032, T033, T036, T039 | Yes | Summary |
| FR-006 | Yes | T041, T044, T045, T048 | Yes | Constraints |
| FR-007 | Yes | T007, T019, T021, T022, T025, T035, T050 | Yes | Storage, Constitution Check VII |
| FR-008 | Yes | T008, T018, T024 | Yes | Constraints |
| FR-009 | Yes | T037, T038 | Yes | Summary |
| FR-010 | Yes | T027, T043, T049 | Yes | Constitution Check I/II |
| SC-001 | Partial | T033 | Yes | Constitution Check I — numeric target not pinned (F-001) |
| SC-002 | Yes | T029, T041, T044, T045 | Yes | Constraints |
| SC-003 | Yes | T019, T029, T035, T050 | Yes | Constitution Check VII |
| SC-004 | Yes | T029, T031, T032, T036 | Yes | Constraints |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | None detected — tech (Python 3.11, pydantic v2, `decimal.Decimal`, pytest-bdd, anthropic) lives in plan.md; spec.md stays implementation-neutral. | — |

## Metrics

- Total requirements: 14 (10 FR + 4 SC)
- Total tasks: 62
- Coverage: 100% (SC-001 numeric threshold unpinned — see F-001)
- Ambiguity count: 2
- Critical: 0 · High: 0 · Medium: 3 · Low: 2
- Total findings: 5

**Health Score**: 93/100 (stable — first run)

## Next Actions
- Pin SC-001's numeric threshold (true-positive and true-negative rates) in spec.md (F-001).
- Add units to FR-008's tolerance declaration in spec.md ("cents", integer) (F-002).
- Widen TS-011's defect class or add a scenario for structurally unparseable rows beyond the two literal-string examples (F-003).
