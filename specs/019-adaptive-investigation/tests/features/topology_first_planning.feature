# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Topology-First Planning on Open Directive
  Open exploratory directives must trigger filename-pattern and regex-search topology mapping before any plan is emitted, and every prioritized plan item must trace back to a concrete discovery.

  Background:
    Given an unfamiliar codebase at a configured target path
    And an open exploratory directive "Add tests for this legacy codebase"
    And an exploration budget sufficient for a full topology pass

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Topology mapping precedes plan emission
    When the coordinator agent is started
    Then the first externally observable tool calls are filename-pattern and regex-search queries over the workspace
    And no plan is emitted before those topology queries complete

  @TS-002 @FR-002 @FR-008 @SC-001 @P1 @acceptance
  Scenario: Emitted plan is structured and grounded in discovered modules
    Given the topology pass has completed and discovered three uncovered modules
    When the agent emits its plan
    Then the plan is a structured ordered list with explicit priority markers
    And each high-priority item references at least one concrete discovered module

  @TS-003 @FR-008 @P1 @acceptance
  Scenario: Every prioritized plan item traces to a topology finding
    Given the agent has emitted its initial plan
    When a reviewer compares each plan item against the recorded topology findings
    Then every prioritized plan item traces back to at least one recorded topology node id

  @TS-004 @FR-001 @SC-001 @P1 @validation
  Scenario: Planner module never constructs a Plan before TopologyMap materializes
    Given a static analysis of katas/019_adaptive_investigation/planner.py
    When the AST lint for topology-first ordering runs
    Then no code path constructs a Plan before a TopologyMap instance is observed in the run

  @TS-005 @FR-002 @P1 @contract
  Scenario: Emitted Plan conforms to the declared JSON schema
    Given a Plan produced by the Planner
    When the plan is validated against contracts/plan.schema.json
    Then the plan passes schema validation with additionalProperties forbidden
    And the steps field is a non-empty ordered array of PlanStep items
