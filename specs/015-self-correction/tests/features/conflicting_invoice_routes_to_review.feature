# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Conflicting Invoice Routes to Human Review
  When the stated total and the recomputed line-item sum disagree beyond tolerance,
  the extractor sets conflict_detected=true, preserves both totals, and routes the
  record to the human-review queue instead of returning it as a clean extraction.

  Background:
    Given an initialized invoice extractor with a declared tolerance_cents
    And a human-review queue at runs/<session-id>/review-queue.jsonl
    And a downstream clean-extraction consumer

  @TS-006 @FR-004 @FR-005 @SC-001 @SC-004 @US-002 @P2 @acceptance
  Scenario: Line-sum mismatch beyond tolerance flags a conflict and routes to review
    Given an invoice whose stated total disagrees with the line-item sum beyond the declared tolerance
    When the extractor runs
    Then conflict_detected is true
    And the record is appended to the human-review queue
    And the record is NOT returned to the downstream clean consumer

  @TS-007 @FR-001 @FR-006 @SC-002 @US-002 @P2 @acceptance
  Scenario: Both totals are preserved unchanged when a conflict is detected
    Given a conflict was detected for an invoice
    When the output record is inspected
    Then stated_total equals the literal document value
    And calculated_total equals the independently recomputed sum
    And neither field has been replaced by the other

  @TS-008 @FR-007 @SC-003 @US-002 @P2 @acceptance
  Scenario: Conflict record carries the full line-item calculation trace
    Given a conflict was detected for an invoice
    When downstream consumers read the record
    Then the record exposes a per-line-item calculation trace
    And a reviewer can pinpoint the discrepancy without re-running the extraction

  @TS-009 @FR-005 @SC-004 @US-002 @P2 @acceptance
  Scenario: Every flagged record appears in the review queue exactly once
    Given a corpus run that produces N flagged records
    When the review queue file is inspected
    Then it contains exactly N entries whose invoice_ids match the flagged set
    And zero flagged records leak to the clean-extraction stream

  @TS-010 @FR-009 @US-002 @P2 @acceptance
  Scenario: Missing line items flag a conflict rather than coercing calculated_total to zero
    Given an invoice with a stated total but no extractable line items
    When the extractor runs
    Then conflict_detected is true
    And calculated_total is NOT silently set to zero to match stated_total
    And the record is routed to the human-review queue

  @TS-011 @FR-009 @US-002 @P2 @acceptance
  Scenario Outline: Unparseable or mismatched inputs produce conflicts, never silent coercions
    Given an invoice whose line items include "<defect>"
    When the extractor runs
    Then conflict_detected is true
    And no defective line is silently treated as zero
    And the record is routed to the human-review queue

    Examples:
      | defect                                    |
      | non-numeric amount "TBD"                  |
      | non-numeric amount "see attached"         |
      | a currency different from the invoice     |
      | mixed currencies across line items        |

  @TS-012 @FR-003 @FR-005 @US-002 @P2 @contract
  Scenario: Review queue entry conforms to the declared schema
    Given a conflict was routed to the review queue
    When the queue entry is validated against contracts/review-queue-entry.schema.json
    Then the entry passes schema validation
    And the entry references a conflict_record_id that resolves to a conflict-record.schema.json record

  @TS-021 @FR-009 @US-002 @P2 @acceptance
  Scenario Outline: Structurally unparseable rows produce conflicts beyond literal-string defects
    Given an invoice line with structural defect "<defect>"
    When the extractor runs
    Then conflict_detected is true
    And cannot_populate_both_totals is true
    And calculated_total is NOT silently coerced to zero
    And the record is routed to the human-review queue

    Examples:
      | defect                                            |
      | missing quantity field                            |
      | missing unit_price field                          |
      | quantity present but typed as non-numeric         |
      | unit_price present but typed as non-numeric       |
      | line item missing line_total and all derivable inputs |
      | line item with negative quantity and no signed-credit declaration |
