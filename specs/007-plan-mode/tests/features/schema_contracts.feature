# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001 @US-002 @US-003
Feature: Schema Contracts for Plan Mode Artifacts
  Every persisted artifact — Plan Document, HumanApprovalEvent, SessionModeTransition, ScopeChangeEvent — MUST validate against its declared JSON schema under contracts/.

  @TS-017 @FR-003 @SC-003 @US-001 @P1 @contract
  Scenario: Plan Document validates against plan-document.schema.json
    Given a PlanDocument written during a kata run
    When the document's structured representation is validated against "contracts/plan-document.schema.json"
    Then validation succeeds
    And the required fields "task_id", "summary", "affected_files", "risks", and "migration_steps" are present

  @TS-018 @FR-001 @FR-005 @SC-002 @US-003 @P3 @contract
  Scenario: HumanApprovalEvent validates against human-approval-event.schema.json
    Given a HumanApprovalEvent emitted by a reviewer
    When the event is validated against "contracts/human-approval-event.schema.json"
    Then validation succeeds
    And the event carries a "plan_hash" field that is a sha256 hex string

  @TS-019 @FR-005 @SC-002 @US-003 @P3 @contract
  Scenario: SessionModeTransition records validate against session-mode-transition.schema.json
    Given a SessionModeTransition appended to the event log
    When the record is validated against "contracts/session-mode-transition.schema.json"
    Then validation succeeds
    And the record carries "session_id", "from_mode", "to_mode", "at", and "reason"

  @TS-020 @FR-004 @FR-007 @SC-004 @US-003 @P3 @contract
  Scenario: ScopeChangeEvent records validate against scope-change-event.schema.json
    Given a ScopeChangeEvent emitted before a blocked out-of-scope edit
    When the record is validated against "contracts/scope-change-event.schema.json"
    Then validation succeeds
    And the record carries "attempted_target", "current_plan_hash", and "affected_files_snapshot"
