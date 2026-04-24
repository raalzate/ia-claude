# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Scoped Fan-Out from Coordinator
  Coordinator decomposes a task, hands each subagent only the declared Subtask Payload fields, and consumes only schema-valid results.

  Background:
    Given a coordinator configured with a task-spawning tool in its allowed tools list
    And a registered HandoffContract pairing a SubtaskPayload schema with a SubagentResult schema
    And the default subagents do not share the task-spawning tool

  @TS-001 @FR-001 @FR-006 @P1 @acceptance
  Scenario: Coordinator emits one scoped payload per subtask
    Given a decomposable task with two independent subtasks
    When the practitioner submits the task to the coordinator
    Then the coordinator emits exactly one SubtaskPayload per subtask
    And each SubtaskPayload is transmitted via the task-spawning tool

  @TS-002 @FR-001 @P1 @contract
  Scenario: Subagent input contains only fields declared by the payload schema
    Given a decomposable task with one subtask
    When the coordinator spawns the subagent
    Then the subagent input contains only fields declared in the SubtaskPayload schema
    And no field outside the SubtaskPayload schema is present in the subagent input

  @TS-003 @FR-003 @P1 @contract
  Scenario: Subagent result validates against the declared Subagent Result schema
    Given a subagent has completed its subtask
    When the subagent returns control to the coordinator
    Then the returned value is a JSON object
    And the returned value validates against the declared SubagentResult schema

  @TS-004 @FR-003 @P1 @acceptance
  Scenario: Coordinator consumes only declared fields of the subagent result
    Given a subagent returns a schema-valid SubagentResult
    When the coordinator incorporates the result into its reasoning
    Then only fields declared in the SubagentResult schema influence coordinator state
    And no undeclared field is absorbed into coordinator state

  @TS-005 @FR-006 @P1 @acceptance
  Scenario: Subagents do not hold the task-spawning tool by default
    Given the coordinator's allowed tools include the task-spawning tool
    When a default subagent is instantiated for a registered role
    Then the subagent's allowed tools list excludes the task-spawning tool

  @TS-006 @P1 @validation
  Scenario: Empty decomposition returns a defined no-op outcome
    Given a task whose decomposition yields zero subtasks
    When the coordinator processes the decomposition
    Then the coordinator returns a defined no-op outcome
    And the coordinator spawns zero subagents
    And the coordinator does not hang or fabricate work
