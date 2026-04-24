# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Approved Plan Unlocks Direct Execution
  A verified HumanApprovalEvent whose plan_hash matches the on-disk Plan Document transitions the session to execute mode; scope changes or hash mismatches halt for re-approval.

  Background:
    Given a Plan Document exists at "specs/fixtures/refactor-plans/<task_id>.md"
    And the session is currently in "plan" mode
    And a HumanApprovalEvent has been produced by a human reviewer

  @TS-011 @FR-001 @FR-005 @SC-002 @US-003 @P3 @acceptance
  Scenario: Matching plan_hash authorizes transition to execute mode
    Given the HumanApprovalEvent.plan_hash equals the sha256 of the Plan Document markdown
    When the session verifies the approval event
    Then the session transitions from "plan" to "execute"
    And a SessionModeTransition is appended to the event log
    And the transition record carries the approving actor identifier
    And the transition record carries the approved plan_hash

  @TS-012 @FR-001 @US-003 @P3 @acceptance
  Scenario: Mismatched plan_hash refuses transition and stays in plan mode
    Given the Plan Document on disk has been edited after approval
    And the HumanApprovalEvent.plan_hash no longer matches the current plan markdown hash
    When the session attempts to transition to "execute"
    Then the transition is refused
    And the session remains in "plan" mode
    And an event is emitted with reason "plan_hash_mismatch"

  @TS-013 @FR-004 @SC-004 @US-003 @P3 @acceptance
  Scenario: Scope change halts execution before dispatching the write
    Given the session has transitioned to "execute" under an approved plan
    When the agent proposes editing a file absent from "plan.affected_files"
    Then a ScopeChangeEvent is emitted before the tool is dispatched
    And the proposed file is not written
    And the session re-enters "plan" mode via a SessionModeTransition with reason "scope_change_detected"

  @TS-014 @FR-004 @SC-004 @US-003 @P3 @acceptance
  Scenario Outline: Scope-change detection rate is 100 percent across injected fixtures
    Given the fixture "<fixture>" is loaded
    When the agent runs through execute mode
    Then every attempted edit outside "plan.affected_files" produces a ScopeChangeEvent
    And the scope-change halt rate for the fixture equals 100 percent

    Examples:
      | fixture                |
      | scope_creep_injection  |

  @TS-015 @FR-005 @SC-002 @US-003 @P3 @acceptance
  Scenario: Every Plan-to-Execute transition is traceable to an approved plan
    Given a completed kata run across the full fixture corpus
    When the event log is inspected for SessionModeTransition entries with to_mode "execute"
    Then every such transition carries a non-null plan_task_id
    And every such transition carries a non-null plan_hash
    And every such transition carries a non-null approved_by
    And the traceability ratio equals 100 percent

  @TS-016 @FR-004 @US-003 @P3 @acceptance
  Scenario: Approval revocation mid-execution halts the session
    Given the session is in "execute" mode under an approved plan
    When a follow-up HumanApprovalEvent is observed with approval_note "revoked"
    Then the session halts execution
    And the session does not continue applying changes without a new approval
