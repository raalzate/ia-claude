# Feature Specification: Structured Human Handoff Protocol

**Feature Branch**: `016-human-handoff`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 16 — Create a clean Human-in-the-Loop transition when a subagent hits a policy gap or operational limit. Detect an escalation precondition, invoke an `escalate_to_human` tool, suspend conversational text generation, and force the model to emit a strictly typed JSON summary payload (customer_id, issue_summary, actions_taken, escalation_reason) so the human operator receives a self-contained package instead of a raw transcript."

## Clarifications

### 2026-04-24 (phase-06 analyze)

- **SC-003**: Tagged *manually-verified*. No automated test enforces the 50% median-resolution-time target across ≥ 20 escalations; the pedagogic structured-vs-prose contrast is demonstrated in the README (plan §Complexity Tracking, `@needs-clarify SC-003`). The quantitative target remains a clarify follow-up.
- **Edge Cases / unknown `customer_id`**: Committed to the explicit sentinel `unknown` (matches feature TS-008). The "or validation failure" alternative is dropped — the contract is singular.

## User Stories *(mandatory)*

### User Story 1 - Escalation suspends chat and emits schema-valid payload (Priority: P1)

A practitioner exercises the agent against a scenario designed to trip an escalation precondition (for example, a refund request that exceeds a configured financial limit, or an aggressive customer demand flagged by policy). When the precondition fires, the agent MUST suspend conversational text generation, invoke the `escalate_to_human` tool, and emit a strictly typed JSON handoff payload that a downstream operator queue can consume without reading the raw transcript.

**Why this priority**: This is the core value of the kata. Without suspension-plus-structured-payload, the Human-in-the-Loop transition (Constitution Principle VI) is not actually enforced — the agent keeps chatting and the operator is left triaging prose. P1 delivers a standalone, demonstrable MVP of the handoff contract.

**Independent Test**: Trigger a crafted scenario that violates the configured policy limit. Confirm (a) no further conversational prose is emitted after the trigger, (b) a single `escalate_to_human` invocation is recorded, and (c) its payload validates against the declared handoff schema with all required fields populated.

**Acceptance Scenarios**:

1. **Given** a configured escalation precondition (operation exceeds financial limit), **When** the practitioner submits a request that crosses the limit, **Then** the agent suspends further conversational output and emits a schema-valid handoff payload containing `customer_id`, `issue_summary`, `actions_taken`, and `escalation_reason`.
2. **Given** an aggressive customer demand flagged by policy, **When** the policy classifier fires, **Then** the agent invokes `escalate_to_human` exactly once and the payload is routed to the operator queue with a traceable escalation id.

---

### User Story 2 - Schema rejects prose-only handoff (anti-pattern defense) (Priority: P2)

A practitioner attempts to coax the agent into producing a prose-only handoff — a free-text narrative rather than the declared structured payload — or into dumping the entire unedited chat transcript as the handoff artifact. The schema layer MUST reject the attempt and force the agent back onto the structured contract.

**Why this priority**: Defending the anti-pattern (raw-transcript dumping or prose-only handoff) is what makes the protocol trustworthy. Without this, the P1 story degrades into "sometimes structured, sometimes a wall of text." P2 guarantees the boundary (Constitution Principle II — Schema-Enforced Boundaries).

**Independent Test**: Issue an escalation under a prompt that explicitly requests prose output or "just paste the transcript." Confirm the schema validator rejects the malformed output and either retries into a valid payload or surfaces a deterministic validation error — never a successful prose handoff.

**Acceptance Scenarios**:

1. **Given** an escalation trigger fires, **When** the agent produces an output lacking one or more required handoff fields, **Then** the schema validator rejects the output and no handoff is delivered to the operator queue.
2. **Given** a practitioner prompt requesting a raw-transcript handoff, **When** the escalation is processed, **Then** the system MUST NOT deliver the raw transcript as the handoff artifact and MUST emit a structured payload or a validation failure.

---

### User Story 3 - Adding a required field propagates across escalations (Priority: P3)

A practitioner extends the handoff schema with a new required field (for example, `severity`). Every subsequent escalation MUST include that field; any escalation that omits it MUST be rejected by the schema layer, without code changes to the agent's prompt logic.

**Why this priority**: Evolvability matters once the protocol is live. Operators will ask for new fields over time (severity, SLA clock, affected region). P3 proves the contract is the source of truth, not hard-coded prompt text.

**Independent Test**: Add `severity` as required in the schema. Re-run the P1 scenario and confirm payloads without `severity` fail validation, and payloads with a valid `severity` value pass.

**Acceptance Scenarios**:

1. **Given** the handoff schema is updated to require `severity`, **When** an escalation fires, **Then** the resulting payload MUST include a valid `severity` value or be rejected by the validator.
2. **Given** a legacy escalation path that does not emit `severity`, **When** it attempts to hand off, **Then** the system MUST surface a schema validation failure rather than silently delivering an incomplete payload.

---

### Edge Cases

- Escalation precondition is tripped mid-tool-call (e.g., partway through a multi-step action). The in-flight tool call MUST be terminated or cleanly finalized before the handoff payload is emitted, and `actions_taken` MUST reflect only completed steps.
- `customer_id` is unknown or not yet bound in the session. The schema MUST emit the explicit sentinel `unknown` (matches feature TS-008) rather than an empty string.
- `actions_taken` list is empty (escalation fires before the agent has taken any action). The payload MUST still validate with an empty list and the `escalation_reason` MUST explain the zero-action trigger.
- Repeated escalations within a single session. Each escalation MUST produce a distinct traceable id; the system MUST NOT collapse duplicate escalations silently.
- Escalation fires while the agent is generating a partial assistant message. Partial conversational output MUST be suppressed from the handoff payload and MUST NOT be delivered to the end user.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST detect a configured escalation precondition (e.g., operation exceeds a declared financial limit, or a policy classifier flags aggressive customer demand) and trigger the handoff path.
- **FR-002**: Upon trigger, the agent MUST suspend further conversational text generation for the remainder of that turn.
- **FR-003**: The agent MUST invoke a single `escalate_to_human` tool call whose arguments conform to the declared handoff schema.
- **FR-004**: The handoff payload MUST include, at minimum, the fields `customer_id`, `issue_summary`, `actions_taken`, and `escalation_reason`.
- **FR-005**: `actions_taken` MUST be a structured list of prior steps the agent performed in the session (not free-form prose).
- **FR-006**: The system MUST reject any escalation output that fails schema validation and MUST NOT deliver it to the operator queue.
- **FR-007**: The system MUST NOT deliver a raw, unedited chat transcript as the handoff artifact (anti-pattern defense).
- **FR-008**: The system MUST NOT deliver a prose-only handoff; structured fields are the contract.
- **FR-009**: The system MUST log each escalation event with a unique traceable id that is persisted in the audit log and referenced in the payload.
- **FR-010**: When the declared handoff schema is extended with a new required field, subsequent escalations MUST be validated against the updated schema without changes to agent prompt logic.
- **FR-011**: The system MUST handle repeated escalations in a single session as distinct events, each with its own traceable id.
- **FR-012**: The documentation MUST describe the escalation preconditions, the handoff schema, and the anti-pattern being defended (per Constitution Principle VIII).

### Key Entities *(include if feature involves data)*

- **Escalation Precondition**: A declarative rule (policy gap or operational limit) that, when satisfied, triggers the handoff path. Attributes: trigger type, threshold or classifier reference, human-readable reason code.
- **Handoff Payload**: The strictly typed JSON summary emitted to the operator queue. Attributes: `customer_id`, `issue_summary`, `actions_taken` (ordered list of prior steps), `escalation_reason`, `escalation_id`, plus any additional required fields declared by the schema.
- **Operator Queue**: The downstream destination that receives validated handoff payloads. Attributes: queue identifier, consumer contract (schema version), ordering guarantees.
- **Escalation Event**: The audit-log record of a single handoff. Attributes: `escalation_id`, timestamp, session reference, precondition that fired, payload snapshot, validation result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of escalations produce schema-valid payloads (zero escalations delivered to the operator queue without passing validation).
- **SC-002**: 0 raw-transcript-only handoffs observed in the operator queue across the evaluation run.
- **SC-003** *(manually-verified)*: Median human resolution time on escalated cases is ≥ 50% lower than the transcript-based baseline, measured over a representative sample of at least 20 escalations. No automated test enforces this threshold — see Clarifications (2026-04-24).
- **SC-004**: Every escalation id is traceable end-to-end in the audit log, linking session, precondition, payload, and operator-queue delivery.
