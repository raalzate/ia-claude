# Requirements Quality Checklist — Kata 6: MCP Integration with Structured Error Handling

**Feature**: `006-mcp-errors`
**Created**: 2026-04-23
**Scope**: Validates that `spec.md` is complete, unambiguous, and aligned with
the workshop's CONSTITUTION.md (v1.2.0) — notably Principle II (Schema-Enforced
Boundaries), Principle VI (Human-in-the-Loop), and Principle VIII (Docs).

- [ ] Every failure case in `spec.md` defines `isError=true` plus the triad `errorCategory`, `isRetryable`, and a detailed explanation (FR-001, FR-002).
- [ ] The anti-pattern — returning a generic `"Operation failed"` string with no category or retryability metadata — is explicitly forbidden in the Functional Requirements and cross-referenced from a Success Criterion (FR-003, SC-002).
- [ ] `errorCategory` is described as an enumerated vocabulary, not a free-form string, satisfying the Schema-Enforced Boundaries principle (FR-002).
- [ ] Retryable vs non-retryable behavior is specified as a deterministic branch on `isRetryable`, not inferred from the explanation text (FR-004, US2).
- [ ] A retry budget exists, is configurable, and its exhaustion has a defined terminal state (escalation), not an infinite loop (FR-005, Edge Cases).
- [ ] Non-retryable failures route to a human-reviewable escalation path, honoring the Human-in-the-Loop principle (FR-008, US2).
- [ ] Network-level failures occurring before an MCP response arrives are covered by a locally-synthesized structured error rather than a raw exception or generic string (FR-007, Edge Cases).
- [ ] Non-conformant MCP payloads (missing required fields) are classified into a dedicated `errorCategory` instead of falling back to a generic message (FR-007, Edge Cases).
- [ ] Every structured error is logged with full metadata and its final outcome (retried-success, retried-exhausted, escalated, aborted) in an inspectable form (FR-006, US3, SC-001).
- [ ] User stories P1, P2, P3 are each independently testable and each state a concrete acceptance scenario that maps to at least one Functional Requirement.
- [ ] Success Criteria are measurable and technology-agnostic — no specific MCP client, server, SDK, or transport is named as a requirement (MCP referenced only as a protocol / domain term).
- [ ] Any numeric target left as a placeholder (e.g., the X% in SC-003) is flagged for `/iikit-clarify` rather than silently shipped as an unreviewed number.
