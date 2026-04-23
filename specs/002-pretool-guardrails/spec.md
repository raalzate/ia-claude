# Feature Specification: Deterministic Guardrails via PreToolUse Hooks

**Feature Branch**: `002-pretool-guardrails`
**Created**: 2026-04-23
**Status**: Draft
**Input**: Kata 2 of the 20-kata workshop for Claude Certified Architect — physically block dangerous or out-of-policy tool invocations using deterministic logic at the PreToolUse boundary, not prompt-only enforcement.

## User Stories *(mandatory)*

### User Story 1 - Refund Within Policy Proceeds Untouched (Priority: P1)

A practitioner asks the agent to process a refund for a customer, and the requested amount falls within the organization's policy limit. The PreToolUse hook inspects the payload, the schema validates, the amount passes the policy threshold, and the tool invocation reaches the external refund API unmodified. The agent reports success to the practitioner.

**Why this priority**: Without a happy path, the guardrail has no baseline of correct behavior. P1 proves the hook does not over-block and that legitimate business flows continue working — a guardrail that rejects everything is indistinguishable from a broken system.

**Independent Test**: A refund request with an amount strictly below the policy limit is submitted. The system is observed to produce exactly one external refund API call with the original payload, and the agent surfaces a success outcome to the practitioner.

**Acceptance Scenarios**:

1. **Given** a configured refund policy with a positive limit, **When** the agent invokes the refund tool with an amount strictly below the limit and a schema-valid payload, **Then** the PreToolUse hook emits an allow verdict and the external API receives exactly one call with the original payload.
2. **Given** a schema-valid in-policy refund request, **When** the external API responds successfully, **Then** the agent conveys a success outcome derived from the real API response, not from a hook-synthesized stub.

---

### User Story 2 - Over-Limit Refund Is Blocked Pre-API by Deterministic Logic (Priority: P2)

A practitioner asks the agent to process a refund that exceeds the configured policy limit. Before the payload can reach the external refund API, a PreToolUse hook inspects the amount field, compares it to the policy, produces a deterministic reject verdict, and emits a structured error back into the model's context. No external API call is made. The model observes the structured error and is forced to react — typically by routing the request to an escalation flow — rather than self-policing via prose. Enforcement is guaranteed by deterministic code at the tool boundary, not by a system-prompt instruction asking the model to behave.

**Why this priority**: This is the core value of the feature and the defense against the named anti-pattern (prompt-only enforcement). Without P2, the "guardrail" is aspirational; with P2, the policy is physically unbypassable even if the model is confused, jailbroken, or fine-tuned differently later.

**Independent Test**: A refund request with an amount strictly above the policy limit is submitted. The system is observed to produce zero external API calls, a structured error object in the model's next context window, and an escalation event in the audit log — all without any change to the system prompt.

**Acceptance Scenarios**:

1. **Given** a configured refund policy with a limit L, **When** the agent invokes the refund tool with an amount strictly greater than L, **Then** the PreToolUse hook emits a reject verdict before any external API call is made and zero refund API requests are observed for that invocation.
2. **Given** a rejected over-limit invocation, **When** control returns to the model, **Then** the model's context receives a structured error payload identifying the policy that was breached, the offending field, and the escalation pathway.
3. **Given** the same over-limit request is retried verbatim, **When** the hook evaluates it, **Then** it is rejected again with an identical verdict — the outcome is deterministic across runs.
4. **Given** a system prompt that does not mention any dollar limit at all, **When** an over-limit refund is attempted, **Then** the request is still blocked — proving enforcement is not prompt-based.

---

### User Story 3 - Policy Change Takes Effect Without Retraining or Prompt Tuning (Priority: P3)

A practitioner (or policy owner) updates the refund limit — for example, from $500 to $250 — in the policy configuration. The next refund invocation is evaluated against the new limit immediately. No model retraining, no fine-tuning, no edit to the system prompt, and no agent redeployment are required. An amount that was previously allowed may now be rejected, and vice versa, purely as a function of the updated policy data.

**Why this priority**: Proves the guardrail is truly data-driven and externalized from the model. Compliance, finance, and risk teams can tighten or loosen limits on their own cadence without an AI release cycle — a key operational property separating deterministic guardrails from prompt-based heuristics.

**Independent Test**: With policy limit L1, submit an amount A where L2 < A < L1 and observe approval. Update the policy limit from L1 to L2 (L2 < L1). Without changing the system prompt or redeploying the model, submit the same amount A again and observe rejection. Verify the audit log cites the new limit L2.

**Acceptance Scenarios**:

1. **Given** a policy limit L1 and an amount A with A < L1, **When** the refund tool is invoked, **Then** the hook allows the invocation.
2. **Given** the policy limit is updated from L1 to L2 where L2 < A < L1, **When** the same refund with amount A is next invoked, **Then** the hook rejects it and cites the updated limit L2 in the structured error and audit log.
3. **Given** a policy change, **When** it takes effect, **Then** no modification to the system prompt, tool schema, or model version is required for the new limit to be enforced.

---

### Edge Cases

- **Missing amount field**: The payload omits the amount entirely. The hook MUST reject with a schema-violation structured error (distinct from a policy-breach error) before any API call.
- **Non-numeric amount**: The amount is a string like "five hundred" or a boolean. The hook MUST reject with a schema-type error; the model MUST NOT be allowed to coerce the value implicitly past the hook.
- **Negative amount**: The amount is below zero (e.g., -100). The hook MUST reject as a schema/domain violation, not silently invert the sign or pass through.
- **Amount exactly at the limit**: The amount equals the policy limit. The policy MUST declare explicitly whether the comparison is strict (<) or inclusive (≤); whichever is chosen, the behavior MUST be deterministic and documented so both audit and tests agree.
- **Hook raises an exception**: The hook itself errors (e.g., corrupted policy file, unreachable policy store). The system MUST fail closed — no tool invocation reaches the external API — and MUST emit a structured error distinguishing "hook failure" from "policy breach" for both the model and the audit log.
- **Payload with extra fields**: The payload contains unexpected fields alongside a valid amount. The hook MUST reject or strip according to an explicit schema stance; silent pass-through is not acceptable.
- **Concurrent policy update mid-invocation**: The policy is updated between payload construction and hook evaluation. The hook MUST evaluate against a single, clearly-scoped policy snapshot, and the audit log MUST record which snapshot was used.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST intercept every refund tool invocation at a PreToolUse boundary that executes strictly before any call to the external refund API.
- **FR-002**: The system MUST validate the tool invocation payload against a declared, versioned schema covering at minimum the presence, type, sign, and numeric bounds of the amount field.
- **FR-003**: The system MUST reject any invocation that fails schema validation with a structured error that identifies the offending field and the validation rule breached.
- **FR-004**: The system MUST reject any invocation whose amount exceeds the currently configured policy limit, regardless of anything stated in the system prompt.
- **FR-005**: The system MUST surface every rejection back into the model's context as a structured error object (not a silent skip, not a free-text apology) so the model observes and can react to the constraint.
- **FR-006**: The system MUST produce zero calls to the external refund API for any invocation that the hook rejects.
- **FR-007**: On a policy-breach rejection, the system MUST emit an escalation event that a human reviewer can act on, consistent with the Human-in-the-Loop principle.
- **FR-008**: The system MUST NOT rely on system-prompt instructions (e.g., "don't refund more than $500") as the mechanism of enforcement; prompt text MAY describe the policy for the model's benefit, but MUST NOT be the control.
- **FR-009**: The system MUST log every rejection with: a timestamp, the policy identifier and version, the offending field and value, the verdict, and a correlation identifier linking the log entry to the model turn and the escalation event.
- **FR-010**: The system MUST produce identical verdicts for identical (payload, policy snapshot) pairs — the hook MUST be deterministic.
- **FR-011**: The system MUST allow the policy limit to be changed via configuration data, with the change taking effect on the next invocation and without requiring any modification to the model, its prompts, or its tool schema.
- **FR-012**: The system MUST fail closed when the hook itself cannot complete evaluation (e.g., policy unreadable, internal exception), treating an indeterminate verdict as a reject with a distinct structured error code.
- **FR-013**: The system MUST document the hook behavior, policy schema, and escalation flow, consistent with the Docs principle.

### Key Entities *(include if feature involves data)*

- **Tool Invocation**: A request, originating from the model, to execute the refund tool. Carries at least a correlation identifier and the payload (including the amount field). Flows through the PreToolUse hook before reaching the external API.
- **Policy**: A versioned, externally-configurable rule set governing what refund invocations are permitted. At minimum carries a policy identifier, a limit value, a comparison stance (strict vs. inclusive at the boundary), and a version or effective-from marker.
- **Hook Verdict**: The deterministic decision produced by the PreToolUse hook for a given (invocation, policy snapshot) pair. Values are allow or reject. A reject verdict carries a reason code (schema violation, policy breach, hook failure) and references the policy identifier and version it was evaluated against.
- **Structured Error Payload**: The machine-parseable object returned into the model's context on a reject verdict. Carries the verdict, reason code, offending field, policy reference, and the designated escalation pathway. Distinct from a free-text message.
- **Escalation Event**: A durable record generated whenever a policy-breach rejection occurs. Carries the correlation identifier, the rejected invocation summary, the policy reference, and the routing target for human review.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of refund invocations whose amount exceeds the configured policy limit are blocked at the PreToolUse hook before reaching the external API, measured over the full acceptance test suite.
- **SC-002**: 0 external refund API calls are observed (via network/audit instrumentation) for any invocation the hook rejected, measured across all rejected invocations in the acceptance test suite.
- **SC-003**: 100% of rejections deliver a structured error object into the model's subsequent context window — there are no silent skips, no empty responses, and no free-text-only rejections — measured by inspecting the post-rejection context for every rejected invocation.
- **SC-004**: A policy-limit change takes effect within one invocation of the change being persisted, with no model retraining, no prompt edit, and no redeployment required, verified by a before/after test using the same payload against the old and new limits.
