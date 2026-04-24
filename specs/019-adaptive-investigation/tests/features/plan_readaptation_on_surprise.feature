# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Plan Re-adaptation on Injected Surprise
  A surprise discovery during execution must force an immutable new plan revision with a logged trigger, and the agent must never continue executing a stale plan step.

  Background:
    Given a coordinator agent with a valid current plan at revision N
    And the agent is executing plan step K
    And a plan-revision log is open for the current session

  @TS-006 @FR-003 @FR-005 @SC-002 @SC-004 @P2 @acceptance
  Scenario: Discovery of unknown external dependency halts step and creates revision
    When a previously unknown external dependency is discovered during step K
    Then the agent halts step K before completing it
    And the agent creates a new plan revision at index N+1
    And the plan-revision log records the discovery as the trigger

  @TS-007 @FR-003 @P2 @acceptance
  Scenario: Resumed execution draws from the revised plan only
    Given a plan revision has been created in response to a surprise
    When execution resumes
    Then the next executed step is drawn from the revised plan
    And no further step is drawn from the stale plan revision

  @TS-008 @FR-003 @SC-002 @P2 @acceptance
  Scenario: External-call surprise inserts an isolation step before any exercising step
    Given the surprise is an external network call that requires isolation
    When the revised plan is emitted
    Then a mocking or isolation step is inserted before any step that would exercise the dependency

  @TS-009 @FR-003 @P2 @validation
  Scenario: Prior plan revisions are immutable once superseded
    Given a plan revision at index N has been superseded by revision N+1
    When the prior revision is inspected
    Then the prior revision record is unchanged from its original write
    And any attempt to mutate the prior revision in place is rejected

  @TS-010 @FR-005 @SC-004 @P2 @contract
  Scenario: Every PlanRevision entry conforms to the declared JSON schema
    Given a plan-revisions.jsonl file produced by a run
    When each record is validated against contracts/plan-revision.schema.json
    Then every record passes schema validation
    And every record carries a non-null trigger with an enumerated category
