# Requirements Quality Checklist: Transactional Memory Preservation via Scratchpad

**Feature**: 018-scratchpad-persistence
**Created**: 2026-04-23

## Checklist

- [ ] The scratchpad file path is explicitly declared and referenced by every functional requirement that writes or reads it (FR-001, FR-003, FR-007).
- [ ] Every user story has at least one acceptance scenario that can be executed without depending on the other stories (US1, US2, US3 independence).
- [ ] The section schema for the scratchpad is declared before any write requirement references it (FR-002, FR-006).
- [ ] The anti-pattern of holding discoveries only inside the live conversation is explicitly defended by a requirement that forces at-the-moment persistence (FR-001) and is covered by a success criterion (SC-001).
- [ ] The anti-pattern of dumping unstructured prose into the scratchpad is explicitly defended by a structural requirement (FR-002, FR-010) and is covered by a success criterion (SC-002).
- [ ] Compaction behavior is specified as a round trip: findings are written on discovery (FR-001) AND read back after `/compact` (FR-009), not just one side.
- [ ] Conflict handling between a new finding and an existing finding is specified rather than left to "last write wins" (FR-004, US2 scenario 3).
- [ ] The size cap and rotation threshold are declared values, not undefined placeholders (FR-005, SC-004).
- [ ] Behavior on a missing scratchpad file is specified as a non-error cold start (FR-007, edge case).
- [ ] Behavior on mid-write termination preserves scratchpad parseability (FR-008, edge case).
- [ ] Success criteria are measurable with a clear pass/fail threshold (SC-001 equals 0, SC-002/SC-003 equal 100%, SC-004 is a hard cap).
- [ ] No functional requirement smuggles in implementation choices (file format, library, storage backend) — the spec stays tech-agnostic while permitting the domain terms `scratchpad` and `/compact`.
