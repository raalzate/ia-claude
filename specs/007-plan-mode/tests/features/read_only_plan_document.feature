# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Large Refactor Triggers a Read-Only Plan Document
  Multi-file refactor requests MUST enter Plan Mode, use only read/search/glob tools, and produce a markdown Plan Document halting for human approval.

  Background:
    Given a fresh session classified as a multi-file refactor request
    And the session mode is initialized to "plan"
    And the Anthropic client is injected with a recorded fixture

  @TS-001 @FR-006 @US-001 @P1 @acceptance
  Scenario: Plan Mode registers only read-class tools with the SDK
    When the agent begins its first turn
    Then the tools passed to messages.create contain only "read_file", "grep", and "glob"
    And no tool name from the WriteTools registry is present in the tools payload

  @TS-002 @FR-003 @SC-003 @US-001 @P1 @acceptance
  Scenario: Plan Mode analysis produces a markdown Plan Document
    Given the agent has completed its read-only analysis turns
    When the agent finalizes the Plan Document
    Then a markdown file is written to "specs/fixtures/refactor-plans/<task_id>.md"
    And the document contains a non-empty "affected_files" section
    And the document contains a "risks" section
    And the document contains an ordered "migration_steps" section

  @TS-003 @FR-001 @US-001 @P1 @acceptance
  Scenario: Agent halts pending human approval after producing the plan
    Given the Plan Document has been written to disk
    When the agent reaches the end of its analysis
    Then the session halts in "plan" mode
    And no SessionModeTransition to "execute" is emitted
    And the halt reason recorded is awaiting human approval

  @TS-004 @FR-003 @SC-003 @US-001 @P1 @acceptance
  Scenario Outline: Plan Document completeness across the refactor corpus
    Given the fixture "<fixture>" is loaded
    When the agent runs Plan Mode to completion
    Then the produced Plan Document lists every affected file in the fixture's expected set
    And the completeness ratio for the fixture equals 100 percent

    Examples:
      | fixture                  |
      | normal_refactor          |
      | scope_creep_injection    |
      | plan_edit_after_approval |
      | infeasible_plan          |

  @TS-005 @FR-006 @US-001 @P1 @acceptance
  Scenario: Infeasible plan is recorded without transitioning to execute
    Given the fixture "infeasible_plan" is loaded
    When the agent concludes the refactor cannot be safely executed
    Then the Plan Document records the infeasibility in its content
    And the session remains in "plan" mode
    And no HumanApprovalEvent is requested for execution

  @TS-006 @FR-006 @US-001 @P2 @acceptance
  Scenario: Small low-risk task bypasses full Plan Document requirement
    Given the fixture "small_refactor" is loaded
    And the request is classified as a single-file low-risk change
    When the agent processes the request
    Then the session records a mode transition with reason "small_refactor_bypass"
    And no multi-file Plan Document is required for the bypass path
