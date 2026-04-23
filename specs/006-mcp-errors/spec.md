# Feature Specification: MCP Integration with Structured Error Handling

**Feature Branch**: `006-mcp-errors`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 6 — Provide actionable feedback to the agent when an MCP-exposed tool fails, using structured error metadata (isError, errorCategory, isRetryable, explanation) so the agent can retry, escalate, or abort deterministically instead of looping blindly on generic failure strings."

## User Stories *(mandatory)*

<!--
  Stories are ordered by priority. Each is independently testable and delivers
  standalone learning value in the workshop kata. The Model Context Protocol
  (MCP) is treated as a domain term; no specific server or client implementation
  is mandated by this spec.
-->

### User Story 1 - Transient Failure with Successful Retry (Priority: P1)

A workshop practitioner invokes an external tool through an MCP server that is
temporarily unavailable (for example, a rate-limit or transient backend error).
The tool returns an MCP response with `isError=true` and a structured payload
containing `errorCategory`, `isRetryable=true`, and a detailed explanation. The
agent reads the metadata, adjusts its call (backoff or payload tweak) within
the configured retry budget, and the next attempt succeeds.

**Why this priority**: This is the canonical motivating scenario of the kata.
Without it, the agent gains nothing over the anti-pattern "Operation failed"
string. Delivering P1 alone proves the structured-error contract works end to
end and is a viable MVP of the kata.

**Independent Test**: Can be fully tested by forcing an MCP-exposed tool to
fail transiently once, observing that the agent receives the structured error,
applies local recovery, and the second invocation succeeds — all without human
intervention.

**Acceptance Scenarios**:

1. **Given** an MCP server exposes a tool that will fail transiently on its
   first call, **When** the agent invokes the tool, **Then** the response
   carries `isError=true`, `errorCategory`, `isRetryable=true`, and an
   explanation field.
2. **Given** the structured error signals `isRetryable=true` and the retry
   budget is not exhausted, **When** the agent adjusts its payload and retries,
   **Then** the subsequent invocation completes successfully and the agent
   surfaces the final result to the practitioner.
3. **Given** a transient failure was retried and resolved, **When** the
   practitioner inspects the run log, **Then** both the structured error and
   the successful retry are recorded with full metadata.

---

### User Story 2 - Validation Failure Routes to Escalation (Priority: P2)

A practitioner triggers an external tool with input that violates the tool's
validation rules (e.g., malformed identifier, unsupported enum value). The MCP
response returns `isError=true`, `errorCategory` identifying a validation
class, `isRetryable=false`, and an explanation. The agent does NOT retry; it
routes the failure to the escalation path defined by policy (handoff,
user-facing clarification prompt, or abort), directly defending against the
anti-pattern of blind retries on a generic "Operation failed" string.

**Why this priority**: This story encodes the anti-pattern defense that the
kata explicitly targets. It proves the metadata is used to branch behavior,
not just decorate logs.

**Independent Test**: Can be fully tested by sending an input known to fail
validation on the MCP-exposed tool and verifying the agent takes the
escalation branch on the first failure, with zero retries executed.

**Acceptance Scenarios**:

1. **Given** a tool call whose input fails validation, **When** the MCP
   response returns `isRetryable=false` with a validation `errorCategory`,
   **Then** the agent performs zero retries against that tool call.
2. **Given** `isRetryable=false`, **When** the agent processes the structured
   error, **Then** it invokes the policy-defined escalation action (human
   handoff, clarification request, or abort with explanation) and records the
   branch taken.
3. **Given** the escalation path completes, **When** the practitioner reviews
   the trace, **Then** it is unambiguous which `errorCategory` drove the
   escalation and no generic failure string appears in the agent context.

---

### User Story 3 - Structured Error Log Inspection and Classification (Priority: P3)

A practitioner reviews the structured error log after a workshop session and
classifies failures by `errorCategory` and `isRetryable`, producing a summary
of how many failures were transient, validation, or non-retryable, and how
many were resolved under the retry budget versus escalated.

**Why this priority**: This story delivers the observability / docs principle
(Constitution VIII) and enables continuous improvement of the kata, but the
system can function with only P1 and P2 in place.

**Independent Test**: Can be fully tested by running a session with a mix of
transient and validation failures, opening the structured error log, and
confirming every entry can be grouped by category and retryability without
needing to read free-form messages.

**Acceptance Scenarios**:

1. **Given** a completed session containing at least one transient and one
   validation failure, **When** the practitioner opens the structured error
   log, **Then** each entry exposes `errorCategory`, `isRetryable`, the
   explanation, and the outcome (retried-success, retried-exhausted,
   escalated, aborted).
2. **Given** the log is loaded, **When** the practitioner filters by
   `errorCategory`, **Then** the count per category and per retryability flag
   is derivable without parsing free-text messages.

---

### Edge Cases

- **Network-level failure before MCP response**: The transport layer drops the
  connection before the MCP server can emit a structured response. The system
  MUST synthesize a structured error locally (category = transport, retryable
  per policy) rather than surfacing a raw exception string.
- **Server returns non-conformant payload**: The MCP server returns
  `isError=true` but omits one or more of `errorCategory`, `isRetryable`, or
  the explanation. The system MUST treat this as a contract violation,
  classify it into a dedicated `errorCategory` (e.g., schema-violation), and
  MUST NOT fall back to a generic failure string.
- **Recoverable failure exceeds retry budget**: A structured error marked
  `isRetryable=true` keeps recurring until the configured retry budget is
  exhausted. The system MUST stop retrying, mark the outcome as
  retried-exhausted, and route to escalation.
- **Multiple chained tool failures**: A single agent turn triggers several
  tool calls that each fail with structured errors of mixed categories and
  retryability. The system MUST handle each independently by its metadata and
  MUST log all of them without collapsing them into a single generic message.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST flag every failed MCP tool invocation with
  `isError=true` in the MCP response.
- **FR-002**: The system MUST include, on every failure response, an
  `errorCategory` value drawn from an enumerated vocabulary, an `isRetryable`
  boolean, and a detailed human-readable explanation.
- **FR-003**: The system MUST NOT emit generic failure strings (e.g.,
  "Operation failed", "Error", "Something went wrong") into the agent context
  in place of, or instead of, the structured payload.
- **FR-004**: The agent MUST branch its behavior on the structured metadata:
  apply local recovery when `isRetryable=true`, and route to
  escalation/abort when `isRetryable=false`.
- **FR-005**: The system MUST enforce a configurable retry budget per tool
  call and MUST stop retrying once the budget is exhausted, transitioning the
  outcome to escalation.
- **FR-006**: The system MUST log every structured error with full metadata
  (category, retryability, explanation, tool identity, attempt count, final
  outcome) in a form that can be inspected and aggregated after the session.
- **FR-007**: When the MCP response is missing required structured fields or
  the connection fails before a response is received, the system MUST
  synthesize a conformant structured error locally rather than surfacing a
  raw exception or generic string.
- **FR-008**: The system MUST keep escalation policy (who or what receives a
  non-retryable failure) explicit and human-reviewable, consistent with the
  Human-in-the-Loop principle.

### Key Entities

- **Tool Call**: An invocation of an external capability exposed by an MCP
  server. Carries the tool identity, the input payload, the attempt count
  against its retry budget, and a link to the resulting MCP Response.
- **MCP Response**: The protocol-level reply to a Tool Call. Carries at least
  an `isError` flag and, on failure, the Structured Error payload.
- **Structured Error**: The failure metadata contract. Fields include
  `errorCategory` (enumerated), `isRetryable` (boolean), `explanation`
  (human-readable), and any contextual hints the agent can use for local
  recovery.
- **Recovery Action**: The agent's response to a Structured Error. Either a
  retry with an adjusted payload (when retryable and within budget), an
  escalation to a human or higher-level policy, or an abort — each recorded
  with its triggering Structured Error.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of observed tool failures in a workshop run carry both an
  `errorCategory` and an `isRetryable` flag — measured by auditing the
  structured error log for missing fields.
- **SC-002**: 0 generic failure strings (e.g., "Operation failed") are
  observable in the agent context across any workshop run — measured by a
  scan of the agent transcript and tool-response log.
- **SC-003**: Retryable failures resolve within the configured retry budget
  in at least X% of runs (target X set during `/iikit-clarify`; placeholder
  90% pending confirmation) — measured by the ratio of retried-success to
  total retryable failures.
- **SC-004**: 100% of non-retryable failures route to the policy-defined
  escalation path and perform zero retries — measured by correlating
  `isRetryable=false` log entries with zero subsequent attempts on the same
  Tool Call.
