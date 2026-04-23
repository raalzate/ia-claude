# Requirements Quality Checklist: Few-Shot Calibration for Edge Cases

**Feature Branch**: `014-few-shot-calibration`
**Spec**: [../spec.md](../spec.md)
**Created**: 2026-04-23

Use this checklist to validate that the specification is complete, unambiguous, technology-agnostic, and aligned with the kata's intent before planning begins.

- [ ] CHK-001 The edge-case task is described in domain terms (e.g., informal measures like "a pinch of salt") with no reference to specific model vendors, APIs, or frameworks.
- [ ] CHK-002 The 2–4 example pair envelope is stated as an explicit, testable bound in both FR-001 and FR-006.
- [ ] CHK-003 Each example pair in the spec uses a structured input/output shape consistent with the Kata 14 illustration (input phrase to typed output object).
- [ ] CHK-004 User Story P1 clearly distinguishes the zero-shot baseline run from the calibrated few-shot run on the same corpus.
- [ ] CHK-005 User Story P2 explicitly names and defends the anti-pattern (zero-shot on subjective/format-sensitive tasks plus iterative prompt tweaking) so it cannot be silently reintroduced later.
- [ ] CHK-006 User Story P3 captures example-set rotation as a sensitivity check, not as a replacement for P1 or P2.
- [ ] CHK-007 Edge Cases cover at minimum: contradictory examples, memorized-training-data leakage, out-of-distribution corpus inputs, and over-long examples.
- [ ] CHK-008 FR-003 and SC-004 together guarantee that every run is traceable to the active example set identifier.
- [ ] CHK-009 FR-005 and SC-003 together guarantee that contradictory example sets fail closed (validation error) rather than silently degrading output.
- [ ] CHK-010 SC-001's improvement threshold is stated as a declared, measurable X% against the zero-shot baseline on the same corpus, not as a vague "better" claim.
- [ ] CHK-011 SC-002 ties calibrated-run output to schema validity, honoring Constitution Principle II (Schema-Enforced Boundaries).
- [ ] CHK-012 The spec contains no technology choices (languages, SDKs, model names, storage) — those belong in plan.md, per Constitution Principle VIII and phase-separation rules.
