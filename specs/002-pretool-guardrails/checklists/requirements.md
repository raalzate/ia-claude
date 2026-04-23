# Requirements Quality Checklist — 002-pretool-guardrails

**Feature**: Deterministic Guardrails via PreToolUse Hooks
**Created**: 2026-04-23
**Status**: Draft

## Content Quality

- [ ] Spec is tech-agnostic: no mentions of specific languages, frameworks, SDKs, or libraries (e.g., Python, Pydantic, FastAPI) — those belong in plan.md.
- [ ] Header fields are correct: Feature Name "Deterministic Guardrails via PreToolUse Hooks", Feature Branch `002-pretool-guardrails`, Created 2026-04-23, Status Draft.
- [ ] The anti-pattern (prompt-only enforcement) is explicitly defended by at least one user story — User Story 2 must demonstrate that enforcement holds even when the system prompt is silent about the limit.
- [ ] Spec aligns with CONSTITUTION.md v1.2.0 Principles I (Determinism), II (Schema-Enforced Boundaries, NON-NEGOTIABLE), VI (Human-in-the-Loop), and VIII (Docs).

## Requirement Completeness

- [ ] Three user stories are present with priorities P1, P2, P3, each independently testable and each with at least one Given/When/Then acceptance scenario.
- [ ] Edge cases cover: missing amount, non-numeric amount, negative amount, amount exactly at the limit, and hook-raises-exception.
- [ ] Functional requirements cover all six mandated behaviors: intercept before external API, validate against declared schema, reject with structured error on policy breach, surface the error back into the model's context, forbid prompt-only enforcement, and log every rejection with a policy reference.
- [ ] Key Entities section defines all five required entities: Tool Invocation, Policy, Hook Verdict, Structured Error Payload, Escalation Event.
- [ ] Every functional requirement is phrased with MUST / MUST NOT and is testable — no vague verbs like "should consider" or "tries to".

## Feature Readiness

- [ ] Success Criteria SC-001 through SC-004 are present, measurable, and technology-agnostic, matching the mandated outcomes (100% over-limit blocked, 0 API calls on reject, 100% structured errors delivered to model context, one-invocation policy turnaround).
- [ ] The behavior at the exact policy boundary (amount == limit) is specified deterministically — strict vs. inclusive is called out rather than left ambiguous.
- [ ] The spec specifies fail-closed behavior when the hook itself errors, distinguishing hook failure from policy breach in the structured error.
- [ ] No [NEEDS CLARIFICATION] markers remain, or every remaining marker is acknowledged and tracked for resolution before moving to plan.md.
