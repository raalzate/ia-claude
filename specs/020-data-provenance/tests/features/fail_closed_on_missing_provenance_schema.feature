# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Fail-Closed on Missing Provenance Schema
  A schema missing any required provenance field must halt the pipeline with a structured validation error — never emit orphan claims, never partial output.

  Background:
    Given the extraction tool input_schema is generated from Claim.model_json_schema()
    And the orphan-claim lint runs as the terminal step of every aggregation pass
    And the pipeline refuses to emit an AggregationReport when orphan claims are present

  @TS-015 @FR-002 @SC-004 @P3 @acceptance
  Scenario Outline: Schema omitting a required provenance field halts with a structured error
    Given a schema that omits the required provenance field "<missing_field>"
    When the pipeline is invoked
    Then execution halts with a validation error naming "<missing_field>"
    And zero claims are emitted
    And zero partial results leak downstream

    Examples:
      | missing_field    |
      | source_url       |
      | source_name      |
      | publication_date |

  @TS-016 @FR-002 @SC-004 @P3 @acceptance
  Scenario: Fully-specified schema proceeds normally with provenance-complete output
    Given a fully-specified extraction schema including claim, source_url, source_name, and publication_date
    When the pipeline runs
    Then the pipeline proceeds to emit an AggregationReport
    And every emitted claim carries populated provenance fields

  @TS-017 @FR-002 @SC-004 @P3 @validation
  Scenario: OrphanClaimError halts emission on the first orphan encountered
    Given a subagent payload that includes a Claim missing source_name
    When the orphan-claim lint runs
    Then the pipeline raises OrphanClaimError
    And the AggregationReport is not written
    And the offending claim_id is reported in the error message

  @TS-018 @FR-002 @P3 @contract
  Scenario: Extraction tool input_schema stays in lockstep with the Claim pydantic model
    Given the Claim pydantic model is inspected
    When the extraction tool definition is compared against Claim.model_json_schema()
    Then the tool input_schema is byte-equivalent to the generated JSON schema
    And adding a required field to Claim propagates to the SDK call without manual edits

  @TS-019 @FR-007 @P3 @validation
  Scenario: tool_choice is pinned to structured extraction on every subagent spawn
    Given a recorded subagent invocation
    When the call arguments are inspected
    Then tool_choice is set to {"type": "any"}
    And the subagent cannot satisfy the contract by returning prose

  @TS-020 @FR-002 @SC-004 @P3 @acceptance
  Scenario: Negative test set achieves 100% orphan-claim rejection rate
    Given the negative test set of schemas each missing at least one provenance field
    When the pipeline is invoked against every negative schema
    Then 100% of invocations fail closed with a structured validation error
    And zero schemas in the negative set produce any emitted claims
