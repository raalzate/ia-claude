# Specification Analysis Report — 005-defensive-extraction

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | Inconsistency | HIGH | plan.md §Source Code; tasks.md T001, T045 | Python package path `katas/005_defensive_extraction/` uses a leading digit in the submodule name. `python -m katas.005_defensive_extraction.runner` will fail. | Rename to `katas/kata_005_defensive_extraction/` across plan and tasks. |
| F-002 | Inconsistency | MEDIUM | tasks.md T012 vs. T039 | T012 authors six fixture cases explicitly listed (`well_formed`, `missing_optional`, `ambiguous_enum`, `contradictory`, `empty_source`, `out_of_enum_value`). T039 later says "Add a `mixed_language/` fixture if not already authored by T012" — but T012 does not include it, so the seventh fixture's authorship is ambiguous. | Decide where `mixed_language/` lives: either add it explicitly to T012 or make T039 own it and drop the "if not already authored" fallback. |
| F-003 | Ambiguity | MEDIUM | spec.md SC-001; plan.md | SC-001 says "zero fabricated values across the full test corpus" — but the auditing mechanism assumes labeled fixtures with `null_map` (plan / quickstart). Live-mode runs (LIVE_API=1) have no labels, so SC-001 is only measurable against fixtures; the live path silently can't be audited. | Clarify in spec SC-001 that the zero-fabrication assertion applies to the labeled fixture corpus, and the live path is advisory. |
| F-004 | Ambiguity | MEDIUM | spec.md FR-005; plan.md T044 | FR-005 requires an escape enumeration ("other"/"unclear") on every enumerated field. `ExtractedRecord` in T006 declares only one enumerated field (`status`). If the model introspects multiple enums, T044's auto-population needs a per-field rule; if not, the "every enumerated field" language is technically unverified. | Restate FR-005 as "every enumerated field in the declared schema" and document the audit that walks all `Literal[...]` fields. |
| F-005 | Terminology | LOW | spec.md Acceptance Scenarios vs. plan.md | Spec refers to the string `"unknown"` as a prohibited "free-form guess"; `FabricationMetric` distinguishes that from a structurally valid null. The contrast between "unknown" (prohibited) and `{"code":"unknown", "raw":...}` markers used in Kata 3 could confuse a reader cross-referencing both katas. | Add a clarification that "unknown" as a free-text fill is forbidden here; the Kata-3 `status.code == "unknown"` marker is a different construct. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | ALIGNED | Branch on `content[0].type == "tool_use"` keys on structured metadata, not prose; no prose fallback. |
| II. Schema-Enforced Boundaries | ALIGNED | `ExtractedRecord` pydantic v2 with `extra="forbid"` (T006); tool `input_schema` is the model's JSON Schema (T018); nullable unions for optional fields (T006). |
| III. Context Economy | ALIGNED | Stable-prefix (schema + instructions) / dynamic-suffix (source) prompt ordering declared in plan. |
| IV. Subagent Isolation | ALIGNED | Not applicable — single-agent kata. |
| V. Test-First Kata Delivery | ALIGNED | Three locked `.feature` files; every TS-NNN cited in tasks; schema lint (T027) and fabrication audit (T028) fail closed. |
| VI. Human-in-the-Loop | ALIGNED | Validation failures surface offending field path and reason (FR-008 / T042). |
| VII. Provenance & Self-Audit | ALIGNED | `FabricationMetric` per-run counter (T029) with per-fixture null_map trace; `AmbiguityMarker` preserves raw observed value (T036). |
| VIII. Mandatory Documentation | ALIGNED | README (T046), module docstrings (T047), why-comments (T048), fallback ladder (T049). |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T008, T018, T044 | Yes | Summary; Constitution Check II |
| FR-002 | Yes | T016, T019 | Yes | Summary; Constraints |
| FR-003 | Yes | T006 | Yes | Constitution Check II |
| FR-004 | Yes | T006, T027, T031, T032 | Yes | Constraints |
| FR-005 | Yes | T007, T009, T036, T041 | Yes | Constitution Check VII |
| FR-006 | Yes | T019, T024, T025 | Yes | Constraints |
| FR-007 | Yes | T029, T030 | Yes | Constitution Check VII |
| FR-008 | Yes | T042 | Yes | Constitution Check VI |
| FR-009 | Yes | T008, T043, T044 | Yes | Constitution Check VIII |
| FR-010 | Yes | T017, T023 | Yes | Constraints |
| SC-001 | Yes | T028, T029, T033 | Yes | Constraints |
| SC-002 | Yes | T016, T017, T019, T020 | Yes | Constraints |
| SC-003 | Yes | T040 | Yes | Summary |
| SC-004 | Yes | T028, T034 | Yes | Constraints |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| _n/a_ | _n/a_ | No violations detected; plan carries tech choices (anthropic, pydantic), spec stays narrative, constitution is untouched. | _n/a_ |

## Metrics

- Total requirements: 14 (FR: 10, SC: 4)
- Total tasks: 55
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 1 · Medium: 3 · Low: 1
- Total findings: 5

**Health Score**: 88/100 (stable — first run)

## Next Actions

- Rename the `005_defensive_extraction` submodule to a Python-legal identifier across plan + tasks.
- Resolve `mixed_language/` fixture ownership: add to T012 or make T039 unconditionally responsible.
- Clarify in `spec.md` SC-001 that zero-fabrication is asserted on the labeled corpus (live path is advisory).
- Document the `Literal[...]`-walk that satisfies FR-005's "every enumerated field" wording.
