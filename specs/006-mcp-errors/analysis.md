# Specification Analysis Report — 006-mcp-errors

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B. Ambiguity | HIGH | spec.md SC-003; plan.md Open Questions | SC-003 carries an unresolved placeholder ("at least 95%") acknowledged in plan.md as NEEDS CLARIFICATION. | Run /iikit-clarify to resolve the threshold before /iikit-04-testify re-run; T065 tracks but still leaves SC-003 un-pinned. |
| F-002 | H1. Traceability | HIGH | tests/features/*.feature | No scenario is tagged with a dedicated @SC-003 corpus-ratio measurement scenario as plan.md expects (`@needs-clarify SC-003`). TS-002 tags @SC-003 but is a retry-within-budget scenario. | Add a dedicated `@SC-003 @needs-clarify` scenario measuring retryable-resolve ratio per plan.md guidance. |
| F-003 | C. Underspecification | MEDIUM | spec.md FR-008 vs. tasks.md T042-T043 | FR-008 requires escalation policy to be "explicit and human-reviewable"; enumerated `reason` set is defined but the "human-reviewable" aspect is only partially realized (file on disk). | Document the human-review path in README (T056) and cite it from FR-008 trace. |
| F-004 | G. Inconsistency | LOW | plan.md Primary Dependencies vs. Kata 1 | Claims "re-used verbatim from Kata 1" for `anthropic`, but Kata 1 exposes no shared module. | Either introduce a shared helper or rephrase as "same pattern as". |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | ALIGNED | Branches on `StructuredError.isRetryable` and `RetryBudget.remaining()` — typed signals, no prose regex. |
| II. Schema-Enforced Boundaries | ALIGNED | Every MCP response, retry budget, escalation payload is pydantic v2 with JSON Schema; extra=forbid implied via T009 declaration; enums closed. |
| III. Context Economy | ALIGNED | `StructuredError.detail` length-capped (1024); JSONL log is single source of truth. |
| IV. Subagent Isolation | ALIGNED | N/A — single-agent kata, documented. |
| V. Test-First Kata Delivery | ALIGNED | /iikit-04-testify precedes /iikit-05-tasks; AST lint fail-closed per T038. |
| VI. Human-in-the-Loop | ALIGNED | Every non-retryable failure and budget-exhaust emits typed EscalationTrigger with closed-set reason. |
| VII. Provenance & Self-Audit | ALIGNED | errors.jsonl one record per attempt with full metadata; T061 archives outputs. |
| VIII. Mandatory Documentation | ALIGNED | T056-T059 ship README, docstrings, why-comments, MCP error contract section. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | YES | T021, T022 | YES | Summary, Trace |
| FR-002 | YES | T008, T021 | YES | Constitution Check, Trace |
| FR-003 | YES | T021, T038, T062 | YES | Constraints, Trace |
| FR-004 | YES | T022, T023, T036 | YES | Constitution Check, Trace |
| FR-005 | YES | T010, T023, T042 | YES | Constraints, Trace |
| FR-006 | YES | T024, T044 | YES | Storage, Trace |
| FR-007 | YES | T039, T040, T041 | YES | Trace |
| FR-008 | YES | T042, T043, T044 | YES | Constitution Check, Trace |
| SC-001 | YES | T063 | YES | Trace |
| SC-002 | YES | T038, T062 | YES | Trace |
| SC-003 | PARTIAL | T065 (parked behind clarify) | YES | Open Questions |
| SC-004 | YES | T064 | YES | Trace |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | No violations detected | — |

## Metrics

- Total requirements: 12 (8 FR + 4 SC)
- Total tasks: 69
- Coverage: 100% (SC-003 partial — placeholder tracked)
- Ambiguity count: 1
- Critical: 0 · High: 2 · Medium: 1 · Low: 1
- Total findings: 4

**Health Score**: 87/100 (stable — first run)

## Next Actions

1. Run /iikit-clarify to resolve SC-003 threshold (blocks T065).
2. Regenerate .feature via /iikit-04-testify to add @SC-003 tagged corpus-ratio scenario.
3. Verify FR-008 human-review path documented in README (T056).
