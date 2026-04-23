# Requirements Quality Checklist: Defensive Structured Extraction with JSON Schemas

**Feature**: `005-defensive-extraction`
**Created**: 2026-04-23
**Scope**: Validates `spec.md` for Kata 5 prior to planning.

## Content Quality

- [x] Spec is technology-agnostic: no references to specific JSON schema libraries, validator implementations, SDKs, or language-specific types (e.g., Pydantic, zod, jsonschema).
- [x] Every user story is independently testable and delivers standalone value; P1 alone constitutes a viable MVP.
- [x] Edge cases enumerate missing required field, value outside enumerated set, mixed-language source, contradictory statements, and empty source.
- [x] Key entities (Source Document, Extraction Schema, Extracted Record, Ambiguity Marker) are described by purpose and attributes, not by implementation.

## Requirement Completeness

- [x] Every functional requirement uses MUST / MUST NOT and is individually testable.
- [x] Requirements explicitly forbid the all-required anti-pattern: FR-003 constrains `required` to guaranteed-present fields, and FR-004 mandates nullable unions for optionals (anti-pattern defense).
- [x] Requirements explicitly forbid unconstrained free-text extraction: FR-002 mandates schema-bound tool calls with forced tool choice, and FR-007 forbids free-text "best guess" for optionals.
- [x] Escape enumeration with paired details field is required for every enumerated field (FR-005), and validation failures are rejected rather than silently coerced (FR-006).
- [x] Traceability to Constitution v1.2.0 is explicit: Principle II (Schema-Enforced Boundaries) via FR-001/002/006/010, Principle VII (Provenance & Self-Audit) via FR-008, Principle VIII (Docs) via FR-009.

## Feature Readiness

- [x] Every success criterion is measurable, technology-agnostic, and tied to a user story or anti-pattern defense (SC-001..SC-004 map to fabrication, schema validity, ambiguity routing, and null fidelity).
- [x] The anti-pattern "mark every field as required" has a dedicated defense visible in the spec (FR-003 + FR-004 + US2) and a measurable outcome (SC-004).
- [x] The anti-pattern "string fields with no null option" has a dedicated defense (FR-004) and is exercised by US2's acceptance scenarios.
- [x] No requirement is tagged [NEEDS CLARIFICATION]; any remaining ambiguities have been resolved before planning begins.

---

## Validation Status

- Reviewed against `spec.md` for 20-kata release gate (FDD Plan-by-Feature phase).
- Verified: all functional requirements testable against structured signals; all success criteria have concrete thresholds; anti-patterns each have a dedicated user story; edge cases enumerated.
- **Totals**: 13 items · 13 checked · 0 deferred · 100% complete.
- **Date**: 2026-04-23
