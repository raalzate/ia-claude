# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Chained Audit of a Multi-File Pull Request
  Decompose a multi-file audit into per-file local analysis followed by an integration-only pass,
  keeping the two output classes distinct and traceable to their originating stage.

  Background:
    Given a MacroTask declaring the ordered stages "PerFileAnalysisStage" then "IntegrationAnalysisStage"
    And a corpus of 15 input files staged for audit
    And a run directory "runs/<task_id>/" reserved for intermediate payloads

  @TS-001 @FR-001 @FR-006 @SC-001 @P1 @acceptance
  Scenario: Chain emits one per-file report per input plus a single integration report
    When the chain runs to completion against the 15-file corpus
    Then the artifact set contains exactly 15 per-file reports
    And the artifact set contains exactly 1 integration report
    And per-file reports and the integration report are persisted as separately addressable artifacts

  @TS-002 @FR-002 @FR-003 @P1 @acceptance
  Scenario: Integration stage prompt consumes accumulated per-file reports, not raw corpus
    Given the per-file stage has completed and persisted "runs/<task_id>/stage-0.json"
    When the integration stage prompt is assembled
    Then the prompt body contains the accumulated per-file reports
    And the prompt body contains an explicit instruction to evaluate only inter-module incoherences
    And the prompt body contains no raw file content from the original corpus

  @TS-003 @FR-003 @P1 @acceptance
  Scenario: Final integration report omits single-file local issues already covered upstream
    Given the chain has produced a FinalReport
    When the FinalReport is inspected
    Then no finding in the FinalReport duplicates a LocalFinding already present in the upstream PerFileBundle
    And every inter_module_finding lists at least two involved files

  @TS-004 @FR-007 @P1 @acceptance
  Scenario: Every artifact records its originating stage for traceability
    Given the chain has completed
    When each persisted IntermediatePayload is inspected
    Then it carries a "stage_index" matching its position in the chain
    And it carries a "stage_name" matching the runtime ChainStage that produced it
    And each LocalFinding carries originating_stage "per_file"
    And each IntegrationFinding carries originating_stage "integration"

  @TS-005 @FR-002 @FR-006 @P1 @contract
  Scenario: Persisted intermediate payloads conform to the declared JSON schema
    Given an IntermediatePayload file at "runs/<task_id>/stage-<n>.json"
    When the file is validated against contracts/intermediate-payload.schema.json
    Then validation passes
    And the payload carries stage_name, produced_by_task, produced_at, and records fields

  @TS-011 @FR-003 @FR-008 @P1 @acceptance
  Scenario: Conflicting per-file findings surface in the integration report rather than silent reconciliation
    Given two per-file reports that assert contradictory facts about the same cross-file symbol
    When the integration stage runs
    Then the integration report contains an IntegrationConflict entry naming the symbol
    And the entry lists both source files by path
    And the entry preserves each per-file claim verbatim under claim_a and claim_b
    And the integration report does NOT coerce the claims into a single reconciled value

  @TS-012 @FR-003 @FR-008 @P1 @validation
  Scenario: Silent reconciliation of conflicting findings is rejected at the integration boundary
    Given per-file reports whose findings conflict on the same symbol
    When an IntegrationFinding is constructed without a matching IntegrationConflict entry
    Then construction raises a ConflictingFindingsNotSurfaced exception
    And no FinalReport is persisted

  @TS-013 @FR-001 @FR-003 @P1 @acceptance
  Scenario Outline: Small-N corpora run the chain with an explicit integration-bypass note
    Given a corpus of "<n>" input files staged for audit
    When the chain runs to completion
    Then the artifact set contains exactly "<n>" per-file reports
    And the FinalReport carries a note equal to "integration-bypass: N<=2"
    And the FinalReport lists zero inter_module_finding entries

    Examples:
      | n |
      | 1 |
      | 2 |
