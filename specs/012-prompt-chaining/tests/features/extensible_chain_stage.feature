# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Extending the Chain With an Additional Stage
  The chain is forward-extensible: appending a new downstream stage (e.g. SecurityScanStage) must
  require zero edits to any earlier stage's file, prompt, or payload contract.

  Background:
    Given an existing MVP chain declaring "PerFileAnalysisStage" then "IntegrationAnalysisStage"
    And both existing stages committed at a known git revision
    And a new SecurityScanStage defined in its own file under "stages/"

  @TS-011 @FR-005 @P3 @acceptance
  Scenario: New downstream stage consumes existing intermediate payloads
    Given the chain is extended by appending SecurityScanStage after IntegrationAnalysisStage
    When the extended chain runs to completion
    Then SecurityScanStage receives a PerFileBundle payload from the existing stage-0 output
    And SecurityScanStage emits a SecurityReport persisted to "runs/<task_id>/stage-2.json"
    And its body carries originating_stage "security" on every finding

  @TS-012 @FR-005 @SC-004 @P3 @validation
  Scenario: Adding the new stage modifies zero earlier stage files
    Given SecurityScanStage has been added to the chain declaration
    When the working tree is diffed against the pre-extension git revision
    Then no change is observed in "stages/per_file.py"
    And no change is observed in "stages/integration.py"
    And no change is observed in "stages/base.py"
    And no change is observed in any upstream stage's output_schema

  @TS-013 @FR-004 @SC-003 @P3 @acceptance
  Scenario: Malformed intermediate payload halts the chain loud
    Given a malformed_payload fixture whose stage-0 output is missing a required field
    When the orchestrator reads the payload before dispatching the next stage
    Then a MalformedIntermediatePayload exception is raised
    And the exception carries stage_index, stage_name, validation_errors, and payload_path fields
    And the chain halts without dispatching any downstream stage

  @TS-014 @FR-008 @SC-003 @P3 @acceptance
  Scenario: Per-file analysis failure surfaces rather than being silently absorbed
    Given a single_file_failure fixture where one file's analysis raised a parse_error
    When the PerFileAnalysisStage completes
    Then the PerFileBundle contains a PerFileAnalysisFailure entry for that file
    And the IntegrationAnalysisStage refuses to run while the bundle carries any failure entries
    And the ChainRun halt record cause is "per_file_analysis_failure"

  @TS-015 @FR-005 @SC-004 @P3 @contract
  Scenario: StageDefinition declarations remain stable after extension
    Given the chain declaration before and after adding SecurityScanStage
    When the serialized StageDefinition list for the earlier stages is compared
    Then stage_index, name, responsibility, max_prompt_tokens, input_schema_ref, and output_schema_ref are byte-identical for every pre-existing stage
