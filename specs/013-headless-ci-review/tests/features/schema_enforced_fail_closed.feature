# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Schema-Enforced Output, Fail Closed on Drift
  Reviewer output must validate against the declared JSON schema; any drift fails the CI job closed with no annotations posted and no regex fallback.

  Background:
    Given the declared CLIOutputEnvelope JSON schema is loaded
    And the CI workflow invoked the Claude Code CLI on a pull request
    And the raw CLI stdout has been captured

  @TS-005 @FR-003 @SC-001 @P2 @acceptance
  Scenario: Schema-valid envelope passes validation and is handed to the mapper
    Given the captured stdout validates against the CLIOutputEnvelope schema
    When the validate_review_output step runs
    Then the step exits zero
    And the validated findings are handed to the annotation mapper

  @TS-006 @FR-003 @FR-004 @SC-001 @P2 @acceptance
  Scenario: Schema-invalid envelope fails the job closed
    Given the captured stdout omits a required field declared in the CLIOutputEnvelope schema
    When the validate_review_output step runs
    Then the step exits non-zero with a schema-violation error
    And no annotations are posted for this run
    And no regex or substring parsing is attempted on the stdout

  @TS-007 @FR-004 @SC-002 @P2 @validation
  Scenario: Mapper source code contains no free-form text parsing
    Given the mapper module "katas/013_headless_ci_review/mapper.py"
    When the AST lint inspects every function in the module
    Then the module does not import the "re" module
    And the module invokes no "re.findall" or "re.search" calls
    And the module invokes no "str.split" against raw CLI stdout
    And the module reads its inputs only from the schema-validated envelope

  @TS-008 @FR-009 @SC-001 @P2 @acceptance
  Scenario: CLI exits non-zero and the job fails closed
    Given the Claude Code CLI exits with a non-zero status
    When the CI workflow evaluates the step result
    Then the job fails with the CLI exit code surfaced in the log
    And stderr is retained in the job log
    And no partial annotations are posted

  @TS-009 @FR-009 @P2 @acceptance
  Scenario: Oversized PR input fails closed with a labeled reason
    Given the set of changed files would exceed the model's usable context window
    When the CI workflow processes the run
    Then the job fails with an oversized-context reason
    And no input is silently truncated
    And no annotations are posted

  @TS-010 @FR-008 @SC-001 @P2 @acceptance
  Scenario: Zero-changed-files PR produces empty findings and posts nothing
    Given the pull request contains no reviewable changed files
    When the reviewer runs
    Then the envelope validates against the schema with an empty findings list
    And zero annotations are posted
    And the job exits zero

  @TS-011 @FR-006 @SC-004 @P2 @acceptance
  Scenario Outline: Raw CLI response is retained regardless of outcome
    Given the CI run terminated with status "<status>"
    When the workflow reaches its upload-artifact step
    Then the file "reviews/<run-id>/raw.json" is uploaded as a retained artifact
    And the file "reviews/<run-id>/stderr.log" is uploaded as a retained artifact

    Examples:
      | status          |
      | success         |
      | schema_failure  |
      | cli_failure     |
      | mapping_failure |
