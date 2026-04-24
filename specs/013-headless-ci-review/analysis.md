# Specification Analysis Report — 013-headless-ci-review

**Generated**: 2026-04-24T00:00:00Z
**Artifacts**: spec.md, plan.md, tasks.md, tests/features/*.feature

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| F-001 | B Ambiguity | MEDIUM | spec.md SC-003 "at least the workshop's target percentage of runs ... (target set by the practitioner at kata execution time)" | SC-003's target is deferred to runtime practitioner input — it is not a hard, checkable gate. | Either pin a numeric default in the spec (e.g., ≥ 95% of schema-valid non-empty runs post annotations) or mark SC-003 as a manually-verified criterion with explicit acknowledgement that no automated test enforces it. |
| F-002 | H2 Traceability | MEDIUM | spec.md Edge "Very large PR exceeds context" + FR-009 | FR-009 says "System MUST fail closed ... whenever the CLI exits non-zero or the input exceeds the usable context window" — plan.md notes detection is "either up front or from a CLI signal" but scenario TS-009 says "Given the set of changed files would exceed the model's usable context window" without specifying the detection mechanism. | Pin the detection mechanism (pre-CLI size check vs CLI signal) in plan.md or note it is implementation-choice and make the scenario vehicle-agnostic. |
| F-003 | G Inconsistency | MEDIUM | tasks.md T041 traceability audit lists `TS-001`..`TS-019` — all 19 scenario IDs mapped; plan.md mentions a potential `TS-020` nowhere but spec.md has 4 SC | All 19 scenarios exist and each maps to a step-def; no `TS-020`. Finding retained as a LOW informational confirmation that the traceability audit is complete. | No change required. Downgrade from MEDIUM if cross-confirmed. |
| F-004 | C Underspec | MEDIUM | spec.md FR-009 "or the input exceeds the usable context window" | No FR or task declares the token-count method or the context-window constant used for the pre-check; feature TS-009 also leaves this opaque. | Add a numeric threshold (configurable constant) and cite it in plan.md Constraints. |
| F-005 | D Phase sep | LOW | plan.md Summary "Delivered under Constitution v1.3.0 principles I (Determinism, NON-NEGOTIABLE), II (Schema-Enforced Boundaries, NON-NEGOTIABLE), and VIII (Mandatory Documentation, NON-NEGOTIABLE)" | Plan cites, not defines, governance principles — acceptable. Informational. | No change required. |

## Constitution Alignment

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Determinism Over Probability | PASS | CI decisions driven by CLI exit code + JSON-schema validator boolean; AST lint (T020) forbids regex/split on raw stdout. |
| II. Schema-Enforced Boundaries | PASS | `--json-schema` bound at CLI; `jsonschema` re-validates on runner; pydantic v2 `ReviewFinding`, `CLIOutputEnvelope`, `AnnotationPayload`. |
| III. Context Economy | PASS | Prompt template stored once (FR-007) and passed by reference; stable guardrails at prompt top. |
| IV. Subagent Isolation | PASS | CLI invocation is a one-shot subagent; only typed JSON envelope crosses the boundary. |
| V. Test-First Kata Delivery | PASS | Feature files locked with DO NOT MODIFY banner; schema-violation and regex-lint scenarios are red-first. |
| VI. Human-in-the-Loop | PASS | Oversized PR and non-zero CLI exit surface as labeled CI failures; human PR reviewer is the escalation target. |
| VII. Provenance & Self-Audit | PASS | `reviews/<run-id>/raw.json` + `stderr.log` retained via `if: always()` for 100% of runs (SC-004). |
| VIII. Mandatory Documentation | PASS | T036 README with six sections + exit-code table; T037 module docstrings; T038 why-comments. |

## Coverage Summary

| Requirement | Has Task? | Task IDs | Has Plan Ref? | Plan Sections |
|-------------|-----------|----------|---------------|---------------|
| FR-001 | Yes | T012, T013 | Yes | Summary, Primary Dependencies |
| FR-002 | Yes | T012, T014, T028, T035 | Yes | Summary, Primary Dependencies |
| FR-003 | Yes | T007, T018, T019, T025, T028, T029, T030 | Yes | Summary, Constraints |
| FR-004 | Yes | T007, T019, T020 | Yes | Constraints |
| FR-005 | Yes | T008, T009, T015, T016, T031, T032 | Yes | Primary Dependencies |
| FR-006 | Yes | T012, T024, T027 | Yes | Storage, Constraints |
| FR-007 | Yes | T011, T033, T034, T035 | Yes | Constraints |
| FR-008 | Yes | T023, T026 | Yes | Constraints |
| FR-009 | Yes | T021, T022 | Yes | Constraints |
| SC-001 | Yes | T013, T014, T018, T019, T021, T022, T023, T035 | Yes | Summary |
| SC-002 | Yes | T020 | Yes | Summary |
| SC-003 | No automated test | T015 (partial) | Yes | Constitution Check VII |
| SC-004 | Yes | T024, T027 | Yes | Summary, Storage |

## Phase Separation

| Artifact | Line | Violation | Severity |
|----------|------|-----------|----------|
| — | — | None detected — tech (Python 3.11, jsonschema, pydantic v2, gh, claude CLI) lives in plan.md; spec.md stays implementation-neutral. | — |

## Metrics

- Total requirements: 13 (9 FR + 4 SC)
- Total tasks: 42
- Coverage: 100% (SC-003 is manually-verified by design)
- Ambiguity count: 2
- Critical: 0 · High: 0 · Medium: 3 · Low: 2
- Total findings: 5

**Health Score**: 93/100 (stable — first run)

## Next Actions
- Pin a default numeric gate or mark SC-003 as manually verified so the coverage table is unambiguous (F-001).
- Declare the oversized-context detection mechanism and token-count method in plan.md (F-002, F-004).
- Keep the T041 traceability audit and AST lint (T020) green — both are the irreversible guardrails for this kata.
