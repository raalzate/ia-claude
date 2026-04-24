# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Leak-Probe Defense Against Shared-Memory Anti-Pattern
  Coordinator's private history, scratchpad, and tool transcripts must never cross the isolation boundary into a subagent's input.

  Background:
    Given a coordinator whose private conversation history is seeded with a unique leak-probe UUID
    And the leak-probe UUID is not part of any subtask's declared payload
    And a per-run audit directory recording subagent_inputs.jsonl and subagent_outputs.jsonl

  @TS-007 @FR-001 @FR-002 @SC-001 @SC-004 @P2 @acceptance
  Scenario: Leak-probe UUID does not appear in any subagent input
    Given a decomposable task with two independent subtasks
    When the coordinator spawns subagents for the task
    Then the count of leak-probe UUID occurrences across all subagent input payloads is zero

  @TS-008 @FR-002 @SC-001 @P2 @acceptance
  Scenario: Coordinator-private scratchpad does not leak into subagent input
    Given the coordinator scratchpad contains a unique sentinel string
    And the sentinel string is not part of any subtask's declared payload
    When the coordinator spawns a subagent
    Then the sentinel string does not appear in the subagent input payload

  @TS-009 @FR-001 @P2 @contract
  Scenario: Forwarding the raw coordinator transcript is rejected as a schema violation
    Given the coordinator attempts to forward its raw conversation transcript as a SubtaskPayload
    When the handoff is evaluated against the SubtaskPayload schema
    Then the handoff is rejected as a schema violation
    And the subagent is not invoked

  @TS-010 @FR-005 @P2 @contract
  Scenario: Audit log captures exact payload and result per subagent
    Given a completed run of a decomposable task
    When an auditor inspects subagent_inputs.jsonl and subagent_outputs.jsonl
    Then each spawned subagent has one payload entry recording the exact SubtaskPayload transmitted
    And each spawned subagent has one result entry recording the exact raw output received
    And each pair can be diffed against the declared SubtaskPayload and SubagentResult schemas

  @TS-011 @FR-007 @P2 @acceptance
  Scenario: Nested subagent spawning applies isolation recursively
    Given a subagent is authorized to spawn a child subagent
    When the parent subagent invokes the task-spawning tool with a scoped payload
    Then the child subagent receives only fields declared in its own SubtaskPayload schema
    And the child subagent input contains none of the parent subagent's prior turns
    And the child subagent input contains none of the coordinator's private history

  @TS-012 @FR-002 @SC-001 @P2 @validation
  Scenario Outline: Coordinator-private content is blocked across representative leak channels
    Given the coordinator holds private content of type "<channel>" containing a unique marker
    When the coordinator spawns a subagent for an unrelated subtask
    Then the marker does not appear in the subagent input payload

    Examples:
      | channel                 |
      | conversation_history    |
      | scratchpad_note         |
      | prior_tool_result       |
      | earlier_user_turn       |
