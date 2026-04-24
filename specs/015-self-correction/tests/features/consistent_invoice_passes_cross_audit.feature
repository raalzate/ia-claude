# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Consistent Invoice Passes Cross-Audit
  Invoice extraction emits both stated_total and calculated_total as independent fields,
  proving the pipeline recomputes rather than echoing the stated figure back.

  Background:
    Given an initialized invoice extractor with a declared tolerance_cents
    And a fixture corpus of recorded invoices
    And a session-scoped extractions.jsonl audit log

  @TS-001 @FR-001 @FR-002 @SC-001 @US-001 @P1 @acceptance
  Scenario: Consistent invoice emits both totals and no conflict
    Given an invoice whose line items sum exactly to the stated total
    When the extractor runs
    Then the output emits stated_total equal to the document's literal value
    And the output emits calculated_total equal to the independent sum of line items
    And conflict_detected is false

  @TS-002 @FR-004 @FR-008 @SC-001 @US-001 @P1 @acceptance
  Scenario: Rounding differences within tolerance do not raise a conflict
    Given an invoice with a rounding-only difference within the declared tolerance
    When the extractor runs
    Then both totals are emitted verbatim without either being overwritten
    And conflict_detected is false
    And the tolerance value used for the comparison is persisted on the record

  @TS-003 @FR-007 @SC-003 @US-001 @P1 @acceptance
  Scenario: Successful extraction attaches a per-line-item calculation trace
    Given an invoice whose line items sum exactly to the stated total
    When the extraction succeeds
    Then a per-line-item calculation trace is attached to the extraction record
    And the trace contains one entry per line item with its extracted amount and running sum

  @TS-004 @FR-001 @FR-003 @US-001 @P1 @contract
  Scenario: Extraction record conforms to the invoice-extraction schema
    Given a successful extraction for a consistent invoice
    When the record is validated against contracts/invoice-extraction.schema.json
    Then the record passes schema validation
    And the record carries stated_total, calculated_total, and conflict_detected fields

  @TS-005 @FR-002 @FR-010 @US-001 @P1 @acceptance
  Scenario Outline: calculated_total reflects the independent sum for varied line shapes
    Given an invoice whose line items are "<shape>"
    When the extractor runs
    Then calculated_total equals the signed sum of every line item's amount
    And conflict_detected is "<conflict>"

    Examples:
      | shape                                 | conflict |
      | all positive amounts                  | false    |
      | mixed positive and credit amounts     | false    |
      | duplicate identical line items        | false    |
      | fractional-quantity amounts           | false    |
