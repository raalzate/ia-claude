# Specification Analysis Report — 002-pretool-guardrails

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | Inconsistency | HIGH | plan.md §Source Code; tasks.md T001, T017, T053, T059, T061 | Python package path `katas/002_pretool_guardrails/` and import `katas.002_pretool_guardrails.runner` use a leading digit in the submodule name. Python identifiers may not start with a digit — the module is not importable via standard `import` / `python -m`. | Rename to e.g. `katas/kata_002_pretool_guardrails/` (as tasks.md Notes line 176 flags as a fallback) and update every reference in `plan.md`, `tasks.md`, and checkpoints. |
| F-002 | Inconsistency / Ambiguity | HIGH | tasks.md Notes §line 176 | Tasks.md acknowledges the package-naming problem and tells the implementer to "adjust in T017 if the import fails", but `plan.md §Source Code` still prescribes the illegal name. The document set contradicts itself about whether the kata can even be imported. | Resolve upstream: pick the canonical package name in `plan.md` and remove the contingent note from `tasks.md`. |
| F-003 | Ambiguity | MEDIUM | spec.md §Edge Cases (Amount exactly at the limit); plan.md; tasks.md T029 | Spec says the comparison stance (strict `<` vs. inclusive `≤`) MUST be declared but leaves the choice open. Plan + tasks pick `strict_less_than`; spec itself does not pin the stance, so the decision lives only in implementation. | Record the chosen stance in `spec.md` Clarifications (or explicitly defer to `plan.md` via a pointer) so reviewers see the commitment without reading the plan. |
| F-004 | Coverage | MEDIUM | tasks.md | FR-013 (document hook behavior, policy schema, escalation flow) is tagged in TS-021 and touched by T053/T056, but no task explicitly authors the policy-schema + escalation-flow section of the README alongside the hook contract. | Split T053/T056 to name the exact README subsections covering policy schema and escalation flow. |
| F-005 | Phase Separation | LOW | plan.md §Constraints | Plan declares the string literal `"$500"` MUST NOT appear in `prompts.py` — this is a governance-style prohibition. It is acceptable in plan because it is a tech-local AST lint detail, but borderline; consider whether this belongs in CONSTITUTION.md as a cross-kata rule. | Keep in plan for now; add a note to CONSTITUTION.md if the "policy numerics never in prompt" rule is meant to apply to every kata that has enforcement thresholds. |
| F-006 | Terminology | LOW | spec.md §Key Entities (Hook Verdict); plan.md | Spec calls the verdict values "allow / reject". Plan/tests use `"allow"` / `"reject"` as string literals, but some step defs use `verdict="allow"` vs. `verdict="reject"`. Minor drift. | Verify step defs match the literal strings in the pydantic `Literal[...]`. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | ALIGNED | Hook branches on pydantic validation + `Decimal` comparison (T016, T028 determinism test). No regex over prose. |
| II. Schema-Enforced Boundaries | ALIGNED | `ToolCallPayload`, `PolicyConfig`, `HookVerdict`, `StructuredError`, `EscalationEvent` are pydantic v2 with `extra="forbid"` (T007–T009). Five JSON Schemas under `contracts/`. |
| III. Context Economy | ALIGNED | Plan explicitly notes it is not load-bearing; structured errors are field-level not prose. |
| IV. Subagent Isolation | ALIGNED | Not applicable — single-agent kata; explicitly noted. |
| V. Test-First Kata Delivery | ALIGNED | Gherkin in `tests/features/`; every TS ID cited in tasks; AST lint anti-pattern guards (T036, T037). |
| VI. Human-in-the-Loop | ALIGNED | Every policy-breach and hook-failure reject emits an `EscalationEvent` (T014, T042). |
| VII. Provenance & Self-Audit | ALIGNED | Append-only JSONL audit log (T012, T044) with correlation id, policy id+version, offending field. |
| VIII. Mandatory Documentation | ALIGNED | README (T053), docstrings (T054), why-comments (T055), hook contract docs (T056). |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T016, T023 | Yes | Summary; Constitution Check I |
| FR-002 | Yes | T007, T030 | Yes | Summary; Constraints |
| FR-003 | Yes | T030, T026 | Yes | Summary |
| FR-004 | Yes | T016, T025, T041 | Yes | Summary; Constitution Check I |
| FR-005 | Yes | T026, T041 | Yes | Summary |
| FR-006 | Yes | T030, T043 | Yes | Constraints |
| FR-007 | Yes | T014, T027, T042 | Yes | Summary; Constitution Check VI |
| FR-008 | Yes | T036 | Yes | Constraints |
| FR-009 | Yes | T012, T044 | Yes | Constitution Check VII |
| FR-010 | Yes | T028, T045 | Yes | Summary |
| FR-011 | Yes | T011, T046, T051 | Yes | Summary; Storage |
| FR-012 | Yes | T011, T016, T034 | Yes | Constraints |
| FR-013 | Partial | T053, T056 | Yes | Constitution Check VIII |
| SC-001 | Yes | T025 | Yes | Summary |
| SC-002 | Yes | T025, T043 | Yes | Constraints |
| SC-003 | Yes | T026, T041 | Yes | Constitution Check VI |
| SC-004 | Yes | T046, T048 | Yes | Storage |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| plan.md | Constraints §line 66 | Prompt-text prohibition ("MUST NOT appear inside the system-prompt module") — borderline governance rule but scoped to a single kata's lint; acceptable in plan. | LOW |

## Metrics

- Total requirements: 17 (FR: 13, SC: 4)
- Total tasks: 63
- Coverage: 100%
- Ambiguity count: 1
- Critical: 0 · High: 2 · Medium: 2 · Low: 2
- Total findings: 6

**Health Score**: 85/100 (stable — first run)

## Next Actions

- Resolve the Python package-name problem upstream in `plan.md` and drop the contingent instruction in `tasks.md` Notes.
- Pin the at-limit comparison stance in `spec.md` Clarifications (even as a pointer to plan).
- Expand T053/T056 to name the README subsections that satisfy FR-013 (policy schema + escalation flow).
- Audit step-def literals vs. pydantic `Literal[...]` to close terminology drift on verdict values.
