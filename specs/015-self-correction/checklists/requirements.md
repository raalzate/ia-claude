# Requirements Quality Checklist: Critical Evaluation & Self-Correction

**Feature**: `015-self-correction`
**Created**: 2026-04-23
**Scope**: Validates that `spec.md` captures the Kata 15 intent — cross-auditing stated vs. calculated totals, flagging conflicts, and defending against the silent-trust anti-pattern.

## Items

- [x] The spec defines `stated_total` and `calculated_total` as two distinct, independently produced fields (FR-001, FR-002).
- [x] The spec requires `calculated_total` to come from an iterative per-line-item sum, not from re-reading the stated figure (FR-002).
- [x] The spec introduces `conflict_detected` as a boolean emitted on every output (FR-003).
- [x] The spec defines a declared, documented tolerance that governs the conflict comparison and requires the tolerance value to be persisted with the output (FR-004, FR-008).
- [x] The spec mandates routing every `conflict_detected=true` record to a human-review queue and forbids returning such records as clean extractions (FR-005, SC-004).
- [x] The spec explicitly defends the anti-pattern: neither total is ever silently overwritten by the other under any condition (FR-006, User Story 3, SC-002).
- [x] The spec requires a per-line-item calculation trace on every extraction, satisfying Principle VII (Provenance & Self-Audit) (FR-007, SC-003).
- [x] The spec forbids coercing missing / unparseable line-item amounts to zero and requires flagging such records as conflicts instead (FR-009, Edge Cases).
- [x] Edge cases cover missing line items, non-numeric amounts, currency mismatches, rounding-only discrepancies, and very long invoices (Edge Cases section).
- [x] User stories P1, P2, and P3 are each independently testable and together cover happy path, conflict routing, and the no-silent-overwrite invariant.
- [x] Success criteria are measurable and technology-agnostic, with explicit targets for conflict-detection accuracy, zero silent overwrites, trace coverage, and queue completeness (SC-001 through SC-004).
- [x] The spec aligns with Principle II (Schema-Enforced Boundaries) by requiring a machine-readable schema carrying `stated_total`, `calculated_total`, `conflict_detected`, and the tolerance, with no out-of-band fallback fields.
- [x] The spec aligns with Principle VIII (Docs) by documenting the tolerance, the trace format, and the human-review routing contract so that reviewers can audit the pipeline without reading code.

---

## Validation Status

- Reviewed against `spec.md` for 20-kata release gate (FDD Plan-by-Feature phase).
- Verified: all functional requirements testable against structured signals; all success criteria have concrete thresholds; anti-patterns each have a dedicated user story; edge cases enumerated.
- **Totals**: 13 items · 13 checked · 0 deferred · 100% complete.
- **Date**: 2026-04-23
