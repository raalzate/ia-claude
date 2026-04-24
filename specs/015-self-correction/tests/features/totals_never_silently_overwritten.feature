# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Neither Total Is Ever Silently Overwritten
  Under every input condition the extractor preserves stated_total and calculated_total
  as distinct fields — no post-processing collapses one into the other, and the
  model is never trusted to assert conflict_detected against the arithmetic truth.

  Background:
    Given a replay corpus covering consistent, conflicting, rounding-only, and degenerate invoices
    And an AST-level silent-overwrite gate over the katas/015_self_correction package
    And a pydantic post-validator that recomputes calculated_total from line items

  @TS-013 @FR-001 @FR-006 @SC-002 @US-003 @P3 @validation
  Scenario: Every record in the corpus carries distinct stated and calculated totals
    Given the replay corpus is executed end-to-end
    When every output record is inspected
    Then stated_total equals the literal document value on every record
    And calculated_total equals the independent recomputation on every record
    And zero records have one field substituted by the other

  @TS-014 @FR-006 @SC-002 @US-003 @P3 @validation
  Scenario: No post-processing step collapses the two totals when a conflict is detected
    Given a conflict was detected for an invoice
    When the record is persisted to extractions.jsonl and the review queue
    Then stated_total and calculated_total remain distinct fields in both sinks
    And no transformation rewrites one field to the value of the other

  @TS-015 @FR-001 @US-003 @P3 @acceptance
  Scenario: Consistent invoices still emit both fields as distinct values
    Given an invoice whose totals agree within tolerance
    When the record is persisted
    Then stated_total and calculated_total are emitted as separate JSON fields
    And both fields retain their originating values even though they agree

  @TS-016 @FR-003 @FR-004 @US-003 @P3 @validation
  Scenario: Model-emitted conflict_detected=false is rejected when arithmetic disagrees
    Given the model emits conflict_detected=false for an invoice
    And the recomputed calculated_total differs from stated_total beyond tolerance
    When pydantic validation runs
    Then a ValidationError is raised
    And conflict_detected cannot be forged by the model output

  @TS-017 @FR-006 @SC-002 @US-003 @P3 @validation
  Scenario: AST gate forbids assignment to stated_total or calculated_total outside the parser
    Given the static AST lint scans the katas/015_self_correction package
    When it encounters assignments to extraction.stated_total or extraction.calculated_total
    Then any assignment outside the initial parse function is flagged as a lint failure
    And the build is blocked until the assignment is removed

  @TS-018 @FR-010 @US-003 @P3 @acceptance
  Scenario: Credit, refund, and discount lines keep their sign in calculated_total
    Given an invoice that includes credit or refund line items with negative amounts
    When the extractor runs
    Then calculated_total equals the signed arithmetic sum of all line items
    And credit or refund signs are NOT flipped or dropped during the recomputation

  @TS-019 @FR-007 @US-003 @P3 @acceptance
  Scenario: Very long invoices receive a full per-line trace, not a summarized subset
    Given an invoice with at least fifty line items
    When the extraction completes
    Then the calculation trace contains one entry per line item
    And no subset or summary substitutes for the per-line log

  @TS-020 @FR-002 @FR-007 @US-003 @P3 @contract
  Scenario: Line item records conform to the declared schema
    Given a persisted extraction record
    When each line item is validated against contracts/line-item.schema.json
    Then every line item passes schema validation
    And each line item carries its extracted amount and contribution to the running sum
