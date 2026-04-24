# Specification Analysis Report — 003-posttool-normalize

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | Inconsistency | HIGH | plan.md §Source Code; tasks.md T001, T014, T031 | Python package path `katas/003_posttool_normalize/` uses a leading digit in the submodule name. Not importable via `python -m katas.003_posttool_normalize.runner`. | Rename to `katas/kata_003_posttool_normalize/` (or equivalent) across plan and tasks. |
| F-002 | Ambiguity | MEDIUM | plan.md §Constraints SC-001 | SC-001 threshold (≥70% reduction) is stated as an AVERAGE over corpus in `tasks.md` Notes, but `spec.md` SC-001 ("no more than 30%") doesn't commit to per-fixture vs. average. Plan + tasks commit to average; spec should mirror. | Add a clarification in `spec.md` SC-001 that the 30% ceiling is corpus-average, not per-fixture, or vice-versa. |
| F-003 | Ambiguity | MEDIUM | plan.md D-006 / tokens.py task T010 | Plan says the tokenizer uses `anthropic` tokenizer "when available" and falls back to a "documented stub counter". The stub's definition is not pinned; different stubs would give different reduction ratios. | Define the stub tokenizer (e.g. whitespace tokens, BPE proxy) explicitly in `plan.md` or `research.md`. |
| F-004 | Coverage | LOW | tasks.md | FR-002 (schema-conformant JSON, bounded field set) is covered by T008/T019/T021 but the "bounded field set" aspect is not separately asserted beyond `extra="forbid"`. Reasonable, but worth an explicit test. | Add an assertion that the generated JSON Schema for `NormalizedPayload` has `additionalProperties: false`. |
| F-005 | Terminology | LOW | spec.md Edge Cases vs. plan.md | Spec uses "parse-degraded"; plan/tasks use `parse_status="degraded"` and `parse_status="empty"`. Minor drift on the marker spelling. | Unify on one form in `spec.md` Clarifications. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | ALIGNED | Normalization is a pure function of `(raw bytes, StatusMapping)`; unknown codes surface as explicit `{"code": "unknown", "raw": ...}` — never inferred label. |
| II. Schema-Enforced Boundaries | ALIGNED | `NormalizedPayload`, `StatusMapping`, `AuditRecord`, `RawToolResponse` are pydantic v2; JSON Schemas under `contracts/`. |
| III. Context Economy | ALIGNED | The hook's raison d'être — SC-001 enforces ≥70% token reduction; flat/shallow shape minimizes attention dilution. |
| IV. Subagent Isolation | ALIGNED | Not applicable — single-agent kata. |
| V. Test-First Kata Delivery | ALIGNED | Gherkin locked; tests before impl (T018–T021 precede T022–T026). |
| VI. Human-in-the-Loop | ALIGNED | `parse_status="degraded"` is an explicit reviewer-facing marker; audit log retains raw bytes. |
| VII. Provenance & Self-Audit | ALIGNED | Append-only JSONL audit log (T031) with SHA-256 roundtrip (T029) — 100% raw retention. |
| VIII. Mandatory Documentation | ALIGNED | README (T040), module docstrings (T041–T047), why-comments (T048), contract section (T049). |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T024, T032 | Yes | Summary; Constitution Check II |
| FR-002 | Yes | T008, T019, T021 | Yes | Constitution Check II |
| FR-003 | Yes | T007, T020, T023 | Yes | Summary; Constraints |
| FR-004 | Yes | T008, T021, T026, T034 | Yes | Constraints |
| FR-005 | Yes | T029, T031, T032 | Yes | Summary; Storage |
| FR-006 | Yes | T024, T034 | Yes | Summary |
| FR-007 | Yes | T022, T025, T026 | Yes | Summary; Constraints |
| SC-001 | Yes | T030, T033 | Yes | Constraints |
| SC-002 | Yes | T021 | Yes | Constraints |
| SC-003 | Yes | T020 | Yes | Constraints |
| SC-004 | Yes | T029, T031 | Yes | Constraints |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| _n/a_ | _n/a_ | No violations detected; lxml choice is in plan (where it belongs) with rationale in research.md. Spec stays narrative. | _n/a_ |

## Metrics

- Total requirements: 11 (FR: 7, SC: 4)
- Total tasks: 55
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 1 · Medium: 2 · Low: 2
- Total findings: 5

**Health Score**: 90/100 (stable — first run)

## Next Actions

- Rename the `003_posttool_normalize` submodule to a Python-legal identifier across plan + tasks.
- Pin the SC-001 measurement shape (per-fixture vs. average) in `spec.md`.
- Define the stub tokenizer precisely so SC-001 is reproducible without the live Anthropic tokenizer.
- Add an explicit `additionalProperties: false` assertion for `NormalizedPayload`'s generated schema.
