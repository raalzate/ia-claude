# Requirements Quality Checklist — Adaptive Investigation (Dynamic Decomposition)

Feature: `019-adaptive-investigation`
Artifact under review: `specs/019-adaptive-investigation/spec.md`

- [ ] Header correctly names the feature "Adaptive Investigation (Dynamic Decomposition)", branch `019-adaptive-investigation`, and Created date `2026-04-23`.
- [ ] User Story P1 requires topology mapping (filename-pattern + regex-search) to occur before any plan is emitted, with acceptance scenarios that make this externally observable.
- [ ] User Story P2 describes an injected external dependency and asserts the agent produces a new plan revision (e.g. a "mock first" step) rather than continuing the stale plan.
- [ ] User Story P3 caps the exploration budget and verifies a structured plan is still produced, defending against endless exploration.
- [ ] The anti-pattern "rigid upfront plan produced before any exploration" is explicitly defended by at least one user story and one functional requirement.
- [ ] The anti-pattern "endless exploration without ever producing a structured plan" is explicitly defended by at least one user story and one functional requirement.
- [ ] Edge Cases cover: trivially small codebase, topology-tool failure, cyclic dependencies, discovery contradicting the original directive.
- [ ] Functional Requirements include MUSTs for: topology-before-plan, structured prioritized plan (not prose), re-plan on invalidation, bounded exploration budget, logged trigger per revision.
- [ ] Key Entities define Exploratory Directive, Topology Map, Plan Revision, Trigger Event, and Budget, each described without leaking implementation choices (no frameworks, languages, or specific tools beyond the allowed Glob/Grep concepts).
- [ ] Success Criteria are measurable and technology-agnostic: SC-001 (plan within budget), SC-002 (surprise triggers revision at target rate), SC-003 (zero endless-exploration runs), SC-004 (every revision has a logged trigger).
- [ ] No requirement, entity, or success criterion names a specific language, framework, database, or vendor product (phase-separation: implementation belongs in `plan.md`).
- [ ] Every high-priority functional requirement has at least one acceptance scenario or success criterion that makes its verification concrete (traceability from FR-XXX to SC-XXX or to a Given/When/Then).
