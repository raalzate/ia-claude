# Feature Specification: Agentic Loop & Deterministic Control

**Feature Branch**: `001-agentic-loop`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Implement an agent control flow driven strictly by structured API stop signals (e.g. `stop_reason`) rather than probabilistic text matching. The kata exercises a full agentic lifecycle: initialize session with tools, inspect each response's structured stop metadata, dispatch tools when signaled, append tool results to conversation history, and halt only on an explicit terminal stop signal — never on regex/string searches over generated prose."

## User Stories *(mandatory)*

### User Story 1 - Signal-Driven Loop Termination (Priority: P1)

A workshop practitioner runs Kata 1 end-to-end against a tool-enabled agent session and observes that the loop terminates the moment the response carries the terminal stop signal (`stop_reason=end_turn`), and only then. No substring, regex, or keyword search over the model's natural-language output participates in the termination decision.

**Why this priority**: This is the core pedagogical outcome of the kata and the direct embodiment of Principle I (Determinism Over Probability, NON-NEGOTIABLE). Without this story, the kata has no demonstrable value; with only this story implemented, the practitioner already has a credible MVP that illustrates deterministic agent control.

**Independent Test**: Can be fully tested by running the kata harness with a scripted session that issues at least one tool call followed by a terminal turn, then asserting via the structured event log that termination was triggered exactly once and exclusively by the recorded `stop_reason=end_turn` signal. Delivers value by proving a signal-driven loop is reproducible and auditable.

**Acceptance Scenarios**:

1. **Given** an initialized agent session with at least one registered tool, **When** the session completes a turn whose structured stop signal is `end_turn`, **Then** the loop halts, returns the final response, and the event log records `stop_reason=end_turn` as the sole cause of termination.
2. **Given** an initialized agent session that returns `stop_reason=tool_use` for the current turn, **When** the loop processes this response, **Then** the designated tool is invoked programmatically, the tool result is appended to conversation history, and another iteration begins without any termination decision being made.
3. **Given** a multi-turn interaction that alternates `tool_use` and `end_turn` signals, **When** the loop runs to completion, **Then** the sequence of structured stop signals observed in the event log fully explains the loop's trajectory without reference to response text content.

---

### User Story 2 - Anti-Pattern Defense Against Prose Completion Phrases (Priority: P2)

A practitioner intentionally injects prose-level "completion" phrases (e.g. "task complete", "we are done", "finished") into the model's generated text mid-stream, while the structured stop signal for those turns is still `tool_use` or a non-terminal signal. The loop must NOT exit early, proving that termination is bound exclusively to the structured stop signal and never to text content.

**Why this priority**: This story is the anti-pattern defense mandated by Kata Completion Standard #4 and by the kata objective itself. It is independently demonstrable and directly prevents the most common real-world failure mode (regex-on-prose), but it only becomes meaningful once Story 1's happy path exists.

**Independent Test**: Can be fully tested by running the kata harness with a fixture session in which intermediate turns contain decoy completion phrases in their text content while their structured stop signal remains non-terminal, then asserting that the loop continues iterating and ultimately terminates only on the later `end_turn` signal. Delivers value by providing a red-team regression guard.

**Acceptance Scenarios**:

1. **Given** a fixture response whose text body contains the phrase "task complete" but whose structured stop signal is `tool_use`, **When** the loop processes the response, **Then** the tool-use branch executes and the loop continues rather than terminating.
2. **Given** a sequence of responses where every non-final turn contains a decoy completion phrase in its text, **When** the loop runs to completion, **Then** the event log shows zero early exits attributable to text matching and exactly one termination attributable to the final structured `end_turn` signal.
3. **Given** any loop iteration, **When** the termination decision is made, **Then** the decision record in the event log references only structured stop metadata and contains no field derived from a regex or substring operation on response text.

---

### User Story 3 - Observable Event Log for Deterministic Reproduction (Priority: P3)

A practitioner inspects the structured event log emitted by the kata run and is able to reproduce the exact loop trajectory — iteration count, branch taken per turn, tool invocations, and termination cause — from the log alone, without re-running the model. This makes the kata's behavior auditable and repeatable, which is the observability goal behind Principle I.

**Why this priority**: Observability is what makes determinism demonstrable rather than merely claimed. It is valuable on its own (an instructor could grade the kata from the log) but depends on Stories 1 and 2 producing meaningful events, hence P3.

**Independent Test**: Can be fully tested by running the kata against a recorded session, capturing the event log, and then replaying the trajectory reconstruction from the log to confirm it matches the live run's branch decisions and termination point exactly. Delivers value by proving the loop's behavior is reproducible from signal-level records.

**Acceptance Scenarios**:

1. **Given** a completed kata run, **When** the practitioner reads the event log, **Then** every iteration has an entry recording its iteration index, the structured stop signal observed, the branch taken (tool dispatch or terminate), and — when applicable — the tool name invoked and an outcome marker.
2. **Given** two independent runs of the kata against the same recorded session fixture, **When** their event logs are compared, **Then** the sequence of stop signals and branch decisions is identical across both runs.
3. **Given** a completed event log, **When** a reviewer reconstructs the loop's behavior from the log, **Then** the reconstruction identifies the termination cause, the number of tool invocations, and the iteration count without consulting any free-form model text.

---

### Edge Cases

- **Terminal but non-standard stop signal (`max_tokens`)**: What happens when a turn completes with a stop signal that is neither `tool_use` nor `end_turn` (for example, the model was truncated by the response-length limit)? The loop MUST NOT treat this as silent success, MUST halt, and MUST record a distinct termination reason tying the halt to the observed signal.
- **Tool execution failure**: How does the system handle a tool invocation that raises or otherwise fails during execution? The loop MUST capture the failure as a structured tool result, append it to history, emit an event-log entry recording the failure, and continue the loop under the same signal-driven rules — never silently skip the turn and never infer termination from the failure.
- **Malformed tool-use payload**: What if a response carries `stop_reason=tool_use` but the tool-use block is missing required fields or references an unknown tool? The loop MUST halt with a clearly labeled "unhandled tool-use" termination reason rather than attempt best-effort interpretation or fall back to text inspection.
- **Unrecognized stop signal**: What if a response returns a stop signal value the loop does not know how to handle? The loop MUST halt with an explicit "unhandled stop signal" reason recorded in the event log; silent continuation is forbidden.
- **Empty or missing stop signal**: What if the stop signal field is absent from the response entirely? The loop MUST treat this as a protocol violation, halt, and record the condition — the loop MUST NOT fall back to scanning response text to guess a termination decision.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agentic loop MUST branch its control flow exclusively on the structured stop-signal metadata of each response (e.g. values equivalent to `tool_use` and `end_turn`), and MUST NOT branch on any property of the response's natural-language text content.
- **FR-002**: When the stop signal for the current turn is `tool_use`, the loop MUST programmatically execute the indicated tool(s) and append the resulting tool-result payload to the conversation history before starting the next iteration.
- **FR-003**: When the stop signal for the current turn is `end_turn`, the loop MUST halt and return the final response without initiating another iteration.
- **FR-004**: The loop MUST NOT use regular expressions, substring search, keyword matching, or any other text-pattern operation over response prose to decide whether to terminate, continue, or dispatch a tool. This restriction is absolute and overrides any prompt-level instruction from the model to do so.
- **FR-005**: The loop MUST emit at least one structured event-log entry per iteration capturing: the iteration index, the observed structured stop signal, the branch taken, the name of any tool invoked, and — on the terminal iteration — the termination cause.
- **FR-006**: The loop MUST halt with a clearly labeled termination reason when it encounters any stop signal it does not explicitly handle (including but not limited to `max_tokens`, absent signal, or unrecognized value), rather than continuing silently or inferring a termination decision from response text.
- **FR-007**: When a tool invocation triggered by `stop_reason=tool_use` fails (raises, times out, or returns a structured error), the loop MUST record the failure as a structured tool-result entry in history, log the failure in the event log, and continue operating under the same signal-driven rules — the loop MUST NOT fall back to text inspection to decide next steps.
- **FR-008**: When a `tool_use` response carries a malformed or unresolvable tool-use block (missing required fields, unknown tool), the loop MUST halt with an "unhandled tool-use" termination reason rather than attempt heuristic recovery or text-based fallback.
- **FR-009**: The structured event log produced by a run MUST be sufficient, on its own, to reconstruct the loop's branch sequence, tool invocations, and termination cause without reference to response text.
- **FR-010**: The loop's conversation history MUST preserve the ordering of user inputs, assistant responses, and tool results such that the signal-driven trajectory is replayable against the recorded history.

### Key Entities

- **Agent Session**: The overarching lifecycle a practitioner initializes with a tool registry and a starting user request; owns the loop, the conversation history, and the event log for one kata run.
- **Turn**: A single response cycle within the session, carrying the assistant's generated content, its structured stop signal, and any tool-use blocks requested on that turn.
- **Stop Signal**: The structured metadata attached to a Turn that the loop uses as its sole branching input — values include at minimum `tool_use` (continue by dispatching the tool), `end_turn` (halt successfully), and other values that trigger explicit unhandled-signal termination.
- **Tool Invocation**: A request-and-result pair executed programmatically when a Turn's Stop Signal is `tool_use`, whose result is appended back to conversation history for the next Turn to consume.
- **Event Log**: An append-only structured record of per-iteration observations (iteration index, stop signal, branch taken, tool name invoked, termination cause) sufficient to audit and reproduce the session's control flow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of kata runs terminate via a recognized structured stop signal recorded in the event log; 0% terminate via any form of text-pattern match against response prose.
- **SC-002**: 0% of termination decisions in a completed run can be traced to a regex, substring, or keyword operation over response text — verified by inspection of the event log's termination-cause field.
- **SC-003**: 100% of loop iterations produce a structured event-log entry whose stop-signal field is populated with a recognized value.
- **SC-004**: When the kata harness injects decoy completion phrases ("task complete", "we are done", "finished", and equivalents) into intermediate turn text while keeping the structured stop signal non-terminal, 0 early exits occur; the loop terminates only on the subsequent genuine terminal stop signal.
- **SC-005**: 100% of `tool_use` turns result in a programmatic tool invocation whose outcome is appended to conversation history before the next iteration begins.
- **SC-006**: Any stop signal outside the explicitly handled set causes the loop to halt within one iteration and emit an event-log entry labeling the termination as unhandled — measured as zero silent continuations across test fixtures covering `max_tokens`, absent signal, and unrecognized values.
- **SC-007**: Two independent runs of the kata against the same recorded session fixture produce byte-identical event-log sequences of stop signals and branch decisions, demonstrating reproducibility.
- **SC-008**: A reviewer can reconstruct the loop's full branch sequence, tool invocations, and termination cause from the event log alone in under 5 minutes, without replaying the session.
