# Requirements Quality Checklist: Softmax Dilution Mitigation

**Feature**: 011-softmax-mitigation
**Created**: 2026-04-23

Use this checklist to validate the completeness, clarity, and consistency of `spec.md` before moving to planning. Each item must be verifiable against the spec alone.

- [ ] Every declared critical rule has an identifier, verbatim text, priority, and compliance target (FR-001, Key Entities).
- [ ] Edge regions (primacy and latency) each have an explicit, declared token budget (FR-001, Key Entities).
- [ ] The compaction threshold is declared as a concrete value within the 50–60% band and is referenced consistently across FR-002, SC-003, and User Story 3.
- [ ] The adversarial request batch used to measure compliance is defined or referenced so P1, P2, and P3 runs are comparable.
- [ ] The compliance target X% in SC-001 is a concrete, testable number, not a placeholder.
- [ ] The mid-placement compliance drop threshold Δ in SC-002 is a concrete, testable number that defends the anti-pattern claim.
- [ ] The anti-pattern (mid-context burying of critical rules) is explicitly defended at render time and regressions are detected (FR-005, FR-006, Edge Cases "Anti-pattern slips back in").
- [ ] Behavior when a critical rule is longer than its edge budget is declared and auditable, not silent truncation (Edge Cases, FR-005).
- [ ] Behavior when multiple critical rules compete for edge real estate is governed by a declared priority ordering (Key Entities, Edge Cases).
- [ ] Compaction is required to preserve critical rules verbatim, and any drift introduced by the summarizer is detected (FR-003, Edge Cases "Compaction collapses critical rule").
- [ ] The fail-closed behavior when a session approaches 100% without a successful compaction is unambiguous (Edge Cases, FR-002, FR-005).
- [ ] Logging is sufficient to reconstruct, after the fact, which rules were placed, where, and which compaction events fired at what capacity (FR-004, FR-007).
- [ ] Every functional requirement (FR-001 … FR-007) traces to at least one user story and at least one success criterion.
