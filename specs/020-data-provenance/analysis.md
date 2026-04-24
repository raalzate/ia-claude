# Specification Analysis Report — 020-data-provenance

**Generated**: 2026-04-24T12:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B Ambiguity | HIGH | spec.md SC-003 ("Conflict detection recall is at or above the workshop target on the seeded conflict set") | A measurable outcome leaves its threshold undefined — "workshop target". Feature TS-012 echoes the same phrasing. Without a concrete recall percentage the criterion is not falsifiable and task T076 can only verify "meets/exceeds target" vacuously. | Run `/iikit-clarify` to set a concrete recall threshold (e.g. ≥100% on seeded conflicts in the labeled corpus, given SC-002 already forbids silent drops). Update feature TS-012 and task T076. |
| F-002 | C Underspec | MEDIUM | spec.md FR-003/edge cases; plan.md aggregator detection | "Conflict" is defined as "contradictory values for the same underlying fact" but the implementation scopes conflict detection to "numeric-token divergence within a canonical_key group" (T045). Non-numeric contradictions (e.g. two sources asserting different policy owners) would not trigger the conflict path. | Align spec FR-003 with the implementation scope (numeric tokens only) or extend the aggregator detector to cover categorical contradictions and update the feature outline. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | Conflict detection branches on canonical-claim-key (sha256) and typed pydantic fields; AST lint (T042) forbids winner-selection symbols. |
| II. Schema-Enforced Boundaries | PASS | All models `extra="forbid"`; tool `input_schema` is `Claim.model_json_schema()` (T009, T067); orphan-claim lint terminal (T063, T064). |
| III. Context Economy | PASS | Plan notes audit logs capture canonical keys + provenance metadata, not full source text. |
| IV. Subagent Isolation | PASS | One subagent per source document; coordinator aggregates only typed `SubagentClaimsPayload` (plan §Constitution Check IV; T027). |
| V. Test-First Kata Delivery | PASS | Three `.feature` files locked; tasks cite TS-IDs; hashes locked. |
| VI. Human-in-the-Loop | PASS | `ConflictSet` → `ReviewTask` route is mandatory; no auto-resolution path exists (T046, T047). |
| VII. Provenance & Self-Audit | PASS (NN anchor) | Kata is the Principle VII anchor — every claim carries `source_url` + `source_name` + `publication_date`; audit artifacts written to `runs/<session-id>/` (T011, T031, T048). |
| VIII. Mandatory Documentation | PASS | README with objective/anti-pattern/run/reflection + docstrings + why-comments (T068–T071). |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T005, T024, T027, T029 | Yes | §Summary; §Constraints |
| FR-002 | Yes | T024, T061, T063, T064, T065 | Yes | §Summary; §Constraints |
| FR-003 | Yes | T043, T044, T045 | Yes | §Summary |
| FR-004 | Yes | T042, T047, T049 | Yes | §Constraints |
| FR-005 | Yes | T043, T046, T047 | Yes | §Summary |
| FR-006 | Yes | T011, T031, T048 | Yes | §Summary |
| FR-007 | Yes | T028, T060 | Yes | §Constraints |
| FR-008 | Yes | T014, T026, T029 | Yes | §Summary |
| SC-001 | Yes | T024, T076 | Yes | §Summary |
| SC-002 | Yes | T042, T043, T076 | Yes | §Summary |
| SC-003 | Partial (qualitative) | T076 | Yes | §Summary (target undefined) |
| SC-004 | Yes | T061, T062, T076 | Yes | §Summary |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| _none_ | — | Tech (`anthropic`, `pydantic`) confined to plan.md; spec.md carries only requirements; no governance rules in plan.md. | — |

## Metrics

- Total requirements: 12
- Total tasks: 76
- Coverage: 100%
- Ambiguity count: 2
- Critical: 0 · High: 1 · Medium: 1 · Low: 0
- Total findings: 2

**Health Score**: 93/100 (stable — first run)

## Next Actions
- Run `/iikit-clarify` on SC-003 to set a concrete recall threshold (likely 100% given SC-002's no-silent-drops discipline).
- Either narrow spec FR-003 to numeric-token divergence (matching the aggregator implementation) or extend the detector to cover categorical contradictions and add test rows.
