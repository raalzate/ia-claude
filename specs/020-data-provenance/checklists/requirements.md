# Requirements Quality Checklist — Kata 20: Data Provenance Preservation

**Feature**: 020-data-provenance
**Created**: 2026-04-23
**Purpose**: Validate that `spec.md` is complete, unambiguous, constitution-aligned, and defends the Kata 20 anti-patterns (amalgamated prose summaries, silent conflict resolution) before planning begins.

## Checklist

- [x] Every functional requirement (FR-001 through FR-008) names a provenance field, a conflict behavior, or a subagent output contract — no vague "handle sources well" wording.
- [x] The required provenance fields `claim`, `source_url`, `source_name`, and `publication_date` are listed identically in FR-001, in the Key Entities section, and in the User Story 1 acceptance scenarios.
- [x] User Story 1 (P1) is independently testable with only two manuals and two subagents — no dependency on US2 or US3 to demonstrate provenance preservation.
- [x] User Story 2 (P2) explicitly defends both Kata 20 anti-patterns: it rejects amalgamated prose summaries AND rejects silent conflict resolution, routing conflicts to a human coordinator.
- [x] User Story 3 (P3) demonstrates fail-closed behavior when required provenance fields are removed from the schema (Constitution II — Schema-Enforced Boundaries).
- [x] Edge cases cover all four required scenarios: missing `publication_date`, file-path `source_url`, duplicate claims across sources, and internal-only source without URL.
- [x] FR-004 and FR-005 together make it structurally impossible for the system to auto-resolve a conflict — there is no fallback path that silently picks a winner.
- [x] FR-006 requires aggregation logging sufficient for Constitution VII (Provenance & Self-Audit) replay — source set, claim count, conflict count.
- [x] FR-007 forbids subagents from emitting prose summaries, reinforcing Constitution IV (Subagent Isolation) via schema-validated JSON contracts.
- [x] Success criterion SC-002 is stated as `0 auto-resolved conflicts` (an absolute, not a percentage) — matching the non-negotiable nature of the anti-pattern defense.
- [x] All success criteria (SC-001 through SC-004) are technology-agnostic and measurable without naming a framework, model vendor, or library.
- [x] Key Entities (Source Document, Claim, Provenance Record, Conflict Set, Review Task) are each referenced by at least one functional requirement or acceptance scenario, with no orphan entities.

---

## Validation Status

- Reviewed against `spec.md` for 20-kata release gate (FDD Plan-by-Feature phase).
- Verified: all functional requirements testable against structured signals; all success criteria have concrete thresholds; anti-patterns each have a dedicated user story; edge cases enumerated.
- **Totals**: 12 items · 12 checked · 0 deferred · 100% complete.
- **Date**: 2026-04-23
