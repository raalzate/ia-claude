# Feature Specification: Strict Subagent Context Isolation

**Feature Branch**: `004-subagent-isolation`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 4 — Strict Subagent Context Isolation (Hub-and-Spoke). Prevent attention degradation by cognitively isolating subagents behind a coordinator that decomposes complex tasks, spawns each subagent with a narrowly scoped prompt containing only the information needed, and receives a typed JSON result. Anti-pattern: assuming shared telepathy or inheriting the coordinator's full history into the subagent context."

## User Stories *(mandatory)*

### User Story 1 - Scoped Fan-Out from Coordinator (Priority: P1)

A practitioner hands a decomposable, multi-part task to a coordinator agent. The coordinator breaks the task into independent subtasks, spawns one subagent per subtask, and hands each subagent only the narrow slice of information required to complete its step. Each subagent returns a structured, schema-conforming JSON payload that the coordinator recomposes into the final answer.

**Why this priority**: This is the core hub-and-spoke pattern. Without scoped fan-out and a typed return contract, there is no isolation benefit — the feature does not exist. All other stories assume this baseline is in place.

**Independent Test**: Can be fully tested by submitting a known decomposable task, inspecting the prompt handed to each subagent (to confirm it contains only the subtask slice), and validating each returned payload against the declared subagent output schema. Delivers a working coordinator-plus-subagent pipeline that completes a real task end-to-end.

**Acceptance Scenarios**:

1. **Given** a decomposable task and a coordinator configured with a task-spawning tool in its allowed tools, **When** the practitioner submits the task, **Then** the coordinator emits one scoped payload per subtask and each subagent receives only the fields declared in the Subtask Payload schema.
2. **Given** a subagent has completed its subtask, **When** it returns control to the coordinator, **Then** the returned value is a JSON object that validates against the declared Subagent Result schema and the coordinator incorporates only the declared fields into its reasoning.

---

### User Story 2 - Leak-Probe Defense Against Shared-Memory Anti-Pattern (Priority: P2)

A practitioner deliberately plants a uniquely identifiable "leak probe" string inside the coordinator's private conversation history (e.g., an earlier user turn, a coordinator scratchpad note, or a tool result the coordinator saw). The practitioner then runs a normal decomposable task and verifies that the leak-probe string never appears in any subagent's input prompt, confirming that subagents do not silently inherit the coordinator's full memory.

**Why this priority**: This story directly defends the stated anti-pattern ("telepathy" / inherited memory). It is the observable proof that isolation is real and not accidental. Without this check, isolation is merely asserted, not verified.

**Independent Test**: Can be fully tested by seeding the coordinator's history with a probe token, running a decomposable task, and scanning every subagent input payload for the probe. A zero-occurrence count across all subagent inputs demonstrates the isolation boundary holds.

**Acceptance Scenarios**:

1. **Given** the coordinator's conversation history contains a unique leak-probe string that is not part of any subtask's declared payload, **When** the coordinator spawns subagents for a decomposable task, **Then** no subagent input contains the leak-probe string.
2. **Given** the coordinator attempts to forward its raw conversation transcript as a subtask payload, **When** the handoff is evaluated against the Subtask Payload schema, **Then** the handoff is rejected as a schema violation before the subagent is invoked.

---

### User Story 3 - Swappable Subagent via Typed Contract (Priority: P3)

A practitioner replaces the implementation of one subagent with a different implementation (different reasoning strategy, different model, different internal prompt) while keeping the declared Handoff Contract unchanged. The coordinator continues to function without any modification, because it depends only on the typed contract, not on the subagent's internals.

**Why this priority**: This story proves the architectural value of the typed contract beyond leak prevention — it enables evolution and substitution. It is P3 because the core isolation goal is already satisfied by P1 and P2; swappability is the compounding benefit on top.

**Independent Test**: Can be fully tested by running a task end-to-end, swapping exactly one subagent implementation behind the same contract, rerunning the same task, and verifying identical coordinator behavior plus schema-valid final output. No coordinator code or prompt change is permitted during the swap.

**Acceptance Scenarios**:

1. **Given** a working coordinator and subagent set, **When** one subagent is swapped for a different implementation that honors the same Handoff Contract, **Then** the coordinator completes the task without any changes to its own configuration or prompt.
2. **Given** a swapped subagent returns output that violates the Handoff Contract, **When** the coordinator receives the result, **Then** the coordinator surfaces a terminal schema-validation error rather than silently proceeding.

---

### Edge Cases

- **Malformed JSON from subagent**: What happens when a subagent returns a string that is not parseable JSON? The coordinator must treat this as a terminal error with no silent fallback.
- **Extra or unexpected fields**: How does the system handle a subagent that returns additional fields beyond the declared Subagent Result schema? Such fields must be rejected or stripped according to the schema's policy, never implicitly absorbed into coordinator state.
- **Empty task list**: What happens when the coordinator decomposes a task and the resulting subtask list is empty? The coordinator must return a defined "no-op" outcome rather than spawn zero subagents and hang, or fabricate work.
- **Nested subagent spawning**: What happens when a subagent itself attempts to spawn further subagents? The isolation contract must apply recursively — a child subagent receives only its own scoped payload and returns its own typed result; it does not inherit the parent subagent's or the coordinator's history.
- **Coordinator private history contains sensitive content**: What happens when the coordinator holds secrets or prior-turn context unrelated to the subtask? None of that content may cross the boundary into subagent input.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST limit each subagent's input to fields declared in a versioned Subtask Payload schema; any field not in the schema MUST NOT be transmitted.
- **FR-002**: System MUST reject any implicit inheritance of the coordinator's conversation history, scratchpads, or tool-call transcripts into a subagent's input context.
- **FR-003**: System MUST validate every subagent's output against a declared Subagent Result schema before the coordinator consumes any part of it.
- **FR-004**: System MUST treat schema validation failures (input or output) as terminal errors with no silent fallback; retries are permitted only under an explicitly declared policy.
- **FR-005**: System MUST log the exact payload handed to each subagent and the exact result received, in a form that an auditor can diff against the declared schemas.
- **FR-006**: System MUST configure the coordinator with a task-spawning tool in its allowed tools list; subagents MUST NOT share that tool by default unless explicitly authorized for nested spawning.
- **FR-007**: System MUST apply the isolation contract recursively, so that nested subagents receive only their own scoped payload and return their own typed result without inheriting parent context.
- **FR-008**: System MUST permit replacement of any subagent's internal implementation without requiring changes to the coordinator, as long as the Handoff Contract is preserved.

### Key Entities *(include if feature involves data)*

- **Coordinator**: The hub agent responsible for decomposing a user task into subtasks, spawning one subagent per subtask with a scoped payload, validating each returned result, and recomposing the final answer. Holds private conversation history that MUST NOT leak into subagent input.
- **Subagent**: A spoke agent that executes exactly one subtask against a scoped input payload and returns a typed result. Has no knowledge of the coordinator's broader task, prior turns, or sibling subagents.
- **Subtask Payload**: The versioned, schema-defined object that specifies the complete and minimal input to a single subagent invocation. Is the only channel of information from coordinator to subagent.
- **Subagent Result**: The versioned, schema-defined object returned by a subagent on completion. Is the only channel of information from subagent back to coordinator.
- **Handoff Contract**: The pairing of a Subtask Payload schema and a Subagent Result schema that together define an interchangeable subagent role. Replacing a subagent implementation is safe when and only when the contract is preserved.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero bytes of coordinator-private conversation history are observable in any subagent's input payload, measured by diffing declared Subtask Payload content against the coordinator's transcript across a representative task suite.
- **SC-002**: 100% of subagent outputs are either schema-valid under the declared Subagent Result schema or quarantined as terminal errors; the system never silently accepts a non-conforming result.
- **SC-003**: Replacing a single subagent implementation with a different implementation that honors the same Handoff Contract requires zero changes to the coordinator's code, prompt, or configuration.
- **SC-004**: The count of occurrences of an injected leak-probe string across all subagent input payloads for a representative task run equals zero.
