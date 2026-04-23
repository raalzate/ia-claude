# Requirements Quality Checklist — Multi-Pass Prompt Chaining

Feature: `012-prompt-chaining`
Created: 2026-04-23

- [ ] Macro task decomposition into declared stages is stated as a MUST (FR-001).
- [ ] Per-file pass responsibility is scoped to local issues only (FR-003, US1 scenarios).
- [ ] Integration pass responsibility is scoped to inter-module incoherences only, with no per-file re-analysis (FR-003, US1 scenario 3).
- [ ] Intermediate payload persistence between stages is required (FR-002).
- [ ] Malformed intermediate payloads cause the chain to fail loud rather than silently degrade (FR-004).
- [ ] Anti-pattern defense: the monolithic single-prompt approach is explicitly identified as a baseline to beat, not the target behavior (US2, SC-001).
- [ ] Per-file reports and the integration report are distinct, separately addressable artifacts (FR-006, US1 scenario 1).
- [ ] Chain extensibility: adding a new stage requires zero changes to existing stages (FR-005, US3, SC-004).
- [ ] Edge case coverage: very small corpus, oversized per-file report, single-file failure, and conflicting findings are all addressed.
- [ ] Success criteria are measurable and technology-agnostic (no framework, model, or vendor named in SC-001..SC-004).
- [ ] Traceability: every artifact records the stage that produced it (FR-007).
- [ ] Failure visibility: per-file analysis failures are surfaced, never silently absorbed (FR-008, SC-003).
