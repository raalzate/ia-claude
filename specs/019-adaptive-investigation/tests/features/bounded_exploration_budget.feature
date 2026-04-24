# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Bounded Exploration Still Produces a Plan
  An exploration budget must be enforced so the agent converges on a structured plan even when topology mapping is incomplete, and truncated runs must be labeled for downstream confidence judgments.

  @TS-011 @FR-004 @SC-001 @SC-003 @P3 @acceptance
  Scenario: Budget exhaustion halts exploration and still yields a structured plan
    Given an exploration budget B of wall-clock seconds, iterations, or tool calls
    And a codebase too large to fully map within budget B
    When the agent is run to completion
    Then the agent halts exploration at or before budget B is exhausted
    And the agent emits a structured prioritized plan

  @TS-012 @FR-006 @P3 @acceptance
  Scenario: Budget-limited plan carries a partial-topology annotation and confidence indicator
    Given the agent halted due to budget exhaustion
    When the emitted plan is inspected
    Then the plan carries an explicit "partial topology" or "budget-limited" annotation
    And the plan carries a confidence indicator

  @TS-013 @FR-004 @SC-003 @P3 @acceptance
  Scenario: No run performs unbounded topology mapping without emitting a plan
    Given a full run transcript across the evaluation cohort
    When the transcript is audited for plan emission
    Then every run emits a structured plan at or before budget exhaustion
    And no run performs unbounded topology mapping without ever emitting a plan

  @TS-014 @FR-004 @FR-005 @SC-004 @P3 @validation
  Scenario: Budget exhaustion is itself a logged trigger event
    Given a run that exhausted its exploration budget
    When the plan-revision log is inspected
    Then the final plan revision carries a trigger whose category identifies budget exhaustion
    And no further plan revisions are accepted after the budget-exhaustion trigger

  @TS-015 @FR-004 @P3 @contract
  Scenario Outline: ExplorationBudget predicates trip on the configured bound
    Given an ExplorationBudget configured with <bound_type> set to <bound_value>
    When the agent reaches or exceeds the configured bound
    Then the budget enforcer fires a budget-exhausted trigger
    And the coordinator emits a final best-effort plan

    Examples:
      | bound_type       | bound_value |
      | max_wall_seconds | 1           |
      | max_revisions    | 1           |
      | max_wall_seconds | 30          |
      | max_revisions    | 5           |
