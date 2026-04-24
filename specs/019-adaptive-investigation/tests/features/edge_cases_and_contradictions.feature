# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001 @US-002 @US-003
Feature: Edge-Case Adaptation and Directive Contradiction Handling
  The agent must surface contradictions, degrade gracefully on tool failures, detect dependency cycles, and avoid revision-log spam when adaptations are trivially identical.

  @TS-016 @FR-007 @SC-004 @P2 @acceptance
  Scenario: Discovery that contradicts the original directive halts with escalation
    Given the directive assumes a hand-written legacy codebase
    When a discovery reveals the codebase is actually generated code that should not be hand-tested
    Then the agent halts execution rather than forcing the directive through
    And the agent surfaces the contradiction as a plan-revision trigger with an unambiguous category

  @TS-017 @FR-001 @FR-005 @P2 @acceptance
  Scenario: Topology tool failure triggers safe-default plan with tooling-unavailable trigger
    Given the filename-pattern or regex-search tool errors or returns no results
    When the agent reacts to the tool outcome
    Then the failure is recorded as a structured trigger event
    And the agent emits a minimal safe-default plan labeled with a tooling-unavailable trigger

  @TS-018 @FR-003 @FR-005 @P2 @acceptance
  Scenario: Cyclic dependency in the topology map forces a revision with an explicit cut point
    Given the topology map contains a cycle among discovered module dependencies
    When the Planner consumes the topology map
    Then the cycle is recorded as a trigger event with a cycle-detected category
    And the emitted plan revision selects an explicit cut point rather than recursing

  @TS-019 @FR-005 @SC-004 @P3 @validation
  Scenario: Duplicate plan revisions are coalesced or flagged to prevent log spam
    Given a plan revision that is functionally identical to the immediately prior revision
    When the revision is submitted to the plan-revision log
    Then the log either coalesces the duplicate with the prior revision
    Or the log flags the duplicate as a no-op revision

  @TS-020 @FR-002 @P3 @acceptance
  Scenario: Trivial topology still produces a plan with a trivial-topology flag
    Given a codebase consisting of a single source file
    When the agent completes its topology pass
    Then the agent emits a structured plan
    And the plan is flagged as trivial-topology rather than fabricating additional structure
