# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Provenance-Preserving Aggregation Across Subagents
  Every emitted claim must carry source_url, source_name, and publication_date traceable to its originating Source Document — no prose summaries, no orphan sentences.

  Background:
    Given two corporate manuals registered in the Source Registry
    And each manual is assigned to its own isolated subagent
    And the extraction tool input_schema mirrors the Claim pydantic model

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Two isolated subagents emit claims with complete provenance
    Given two corporate manuals ingested by two isolated subagents
    When the aggregator requests claim extraction
    Then the output is a JSON array of claim records
    And every claim record contains a non-empty claim field
    And every claim record contains a non-empty source_url field
    And every claim record contains a non-empty source_name field
    And every claim record contains a non-empty publication_date field

  @TS-002 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Each emitted claim links back to its exact source document
    Given a single factual claim appears in a source manual
    When the pipeline emits the claim
    Then the emitted record links back to the exact source document
    And the emitted record is not merged into a prose summary

  @TS-003 @FR-001 @FR-007 @SC-001 @P1 @acceptance
  Scenario: No amalgamated prose survives aggregation of N manuals
    Given an aggregation pass across N corporate manuals
    When the output is inspected
    Then zero claims appear without provenance metadata
    And zero amalgamated prose paragraphs are present in the output
    And zero orphan sentences are present in the output

  @TS-004 @FR-007 @P1 @validation
  Scenario: Subagents are forbidden from returning prose summaries
    Given a subagent attempts to return a free-text prose summary
    When the coordinator validates the subagent payload
    Then the payload is rejected as a schema violation
    And the coordinator does not attempt to parse prose back into claims

  @TS-005 @FR-001 @P1 @contract
  Scenario: Emitted claim records conform to the Claim JSON schema
    Given a SubagentClaimsPayload produced by a subagent
    When each claim is validated against contracts/claim.schema.json
    Then every claim passes schema validation
    And every claim carries claim, source_url, source_name, and publication_date fields

  @TS-006 @FR-008 @P1 @acceptance
  Scenario: Duplicate claim text from different sources preserves both provenance records
    Given two sources produce identical claim text
    When the aggregator processes the claims
    Then both provenance records are preserved as separate entries
    And deduplication does not strip source metadata from either entry

  @TS-007 @FR-001 @P1 @acceptance
  Scenario Outline: Edge-case provenance fields are preserved verbatim
    Given a source document with <edge_case>
    When the subagent emits a claim from that source
    Then the emitted claim preserves <preserved_field> verbatim
    And the pipeline does not fabricate a replacement value

    Examples:
      | edge_case                       | preserved_field                                |
      | a local file path as source_url | source_url set to the file path                |
      | no URL at all (internal-only)   | source_url set to null with source_name filled |
      | an undated internal memo        | publication_date sentinel set to "unknown"     |
