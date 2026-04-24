# Specification Analysis Report — 009-path-rules

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B. Ambiguity | MEDIUM | spec.md SC-001 "small measurement tolerance" | "Within a small measurement tolerance" is not quantified. Plan.md calls it a byte-level parity check but spec text still lacks a number. | Quantify tolerance (e.g., 0 bytes — byte parity) in the spec or a clarifications section. |
| F-002 | B. Ambiguity | LOW | spec.md edge case "very large rule file" | "Large enough to dominate the context budget" — plan/tasks pin 20,000 bytes default, overridable via env. | Acceptable given plan refinement; consider cross-referencing from the spec edge case. |
| F-003 | G. Inconsistency | LOW | feature @TS-005 vs. tasks.md contract T018 | @TS-005 asserts "turn_id, edited_path, activated_rules, and timestamp" — tasks.md T046 asserts "(turn_id, timestamp, edited_path, rule_file, matched_pattern, precedence)". Field names differ (`activated_rules` plural vs. per-event `rule_file`). | Reconcile schema field name — contract tests will surface it; confirm via `rule-activation-event.schema.json`. |
| F-004 | C. Underspecification | LOW | spec.md FR-007 | FR-007 prohibits "domain-specific heuristics" in `CLAUDE.md` but does not define the keyword allowlist; plan/tasks defer to a lint keyword allowlist (T027). | Document the allowlist heuristic in README or a clarifications block. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | ALIGNED | Pure glob comparison (`PurePath.match` + `fnmatch.fnmatchcase`); precedence fully specified. |
| II. Schema-Enforced Boundaries | ALIGNED | Pydantic v2 models for RuleFile/MatchingEvent/LoaderDiagnostic; JSON Schemas under contracts/; frontmatter validated via `model_validate`. |
| III. Context Economy | ALIGNED | Load-bearing. Zero-activation byte-delta test (T028, T031) asserts baseline parity; rule bodies appended only when match occurs. |
| IV. Subagent Isolation | ALIGNED | N/A — single loader. |
| V. Test-First Kata Delivery | ALIGNED | /iikit-04-testify precedes /iikit-05-tasks; fixtures gate step defs. |
| VI. Human-in-the-Loop | ALIGNED | FrontmatterError halts load with typed reason set. |
| VII. Provenance & Self-Audit | ALIGNED | MatchingEvent JSONL per activation (turn_id, edited_path, rule_file, matched_pattern). |
| VIII. Mandatory Documentation | ALIGNED | T052-T055 ship README, docstrings, why-comments, precedence/glob docs. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | YES | T008, T019, T020 | YES | Trace |
| FR-002 | YES | T029, T030 | YES | Constraints, Trace |
| FR-003 | YES | T007, T008, T048 | YES | Constraints, Trace |
| FR-004 | YES | T010, T038, T045 | YES | Constraints, Trace |
| FR-005 | YES | T011, T018, T021, T042 | YES | Trace |
| FR-006 | YES | T029, T030 | YES | Trace |
| FR-007 | YES | T027 | YES | Constraints, Trace |
| SC-001 | YES | T028, T031 | YES | Testing, Trace |
| SC-002 | YES | T014, T017, T018, T020 | YES | Trace |
| SC-003 | YES | T039, T044, T048 | YES | Trace |
| SC-004 | YES | T017, T046 | YES | Trace |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | No violations detected | — |

## Metrics

- Total requirements: 11 (7 FR + 4 SC)
- Total tasks: 61
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 0 · Medium: 1 · Low: 3
- Total findings: 4

**Health Score**: 97/100 (stable — first run)

## Next Actions

1. Quantify SC-001 "small measurement tolerance" (plan implies 0 bytes — byte parity).
2. Reconcile MatchingEvent schema field names between @TS-005 and T046 via `rule-activation-event.schema.json`.
3. Document CLAUDE.md keyword allowlist for FR-007 in README.
