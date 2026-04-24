# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Conflict Surfacing Without Silent Resolution
  Contradictory claims across sources must be flagged with conflict_detected=true, preserve both provenance records, and route to a human reviewer — never auto-resolved.

  Background:
    Given two corporate manuals registered in the Source Registry
    And each manual is assigned to its own isolated subagent
    And the ProvenanceAggregator groups claims by canonical-claim-key

  @TS-008 @FR-003 @SC-002 @P2 @acceptance
  Scenario: Two conflicting numeric claims surface as a conflict record
    Given two manuals with conflicting numeric claims for the same fact
    When aggregation completes
    Then the output contains a conflict_detected=true marker
    And both claims appear as full provenance records under the conflict entry

  @TS-009 @FR-004 @FR-005 @SC-002 @P2 @acceptance
  Scenario: Detected conflict is routed to human review without a winning value
    Given a conflict is detected between two source manuals
    When the pipeline reports the conflict
    Then a human-review task is created referencing the conflict canonical_key
    And the pipeline does not emit a single winning value
    And both original provenance blocks appear in the review task hand-off payload

  @TS-010 @FR-003 @SC-002 @P2 @acceptance
  Scenario: Agreeing sources produce no false-positive conflict marker
    Given two sources agree on the value of a fact
    When the aggregator processes the claims
    Then no conflict_detected marker is emitted for that canonical_key
    And the claims appear as a single ClaimGroup with two supporting sources

  @TS-011 @FR-004 @P2 @validation
  Scenario Outline: Forbidden auto-resolution heuristics are absent from the aggregator
    Given the ProvenanceAggregator implementation is scanned
    When the AST lint inspects aggregator.py
    Then the forbidden symbol "<forbidden>" is not present

    Examples:
      | forbidden         |
      | pick_latest       |
      | majority_vote     |
      | confidence_score  |
      | sort_by_date      |

  @TS-012 @FR-003 @SC-003 @P2 @acceptance
  Scenario: Every seeded contradiction in the labeled corpus is detected
    Given the labeled corpus contains N seeded contradictions
    When the aggregator runs across the corpus
    Then conflict detection recall meets or exceeds the workshop target
    And no planted contradiction is silently dropped

  @TS-013 @FR-005 @P2 @contract
  Scenario: ConflictSet and ReviewTask records conform to their JSON schemas
    Given an AggregationReport produced by an aggregation pass with conflicts
    When each ConflictSet is validated against contracts/conflict-set.schema.json
    And each ReviewTask is validated against contracts/review-task.schema.json
    Then every ConflictSet passes schema validation
    And every ReviewTask passes schema validation
    And every ReviewTask's conflict_set_key matches an existing ConflictSet canonical_key

  @TS-014 @FR-006 @P2 @acceptance
  Scenario: Aggregation pass logs sources, claim count, and conflict count for audit
    Given an aggregation pass has completed
    When the aggregation_report.json artifact is inspected
    Then the report records the set of source documents consulted
    And the report records the number of claims emitted
    And the report records the number of conflicts surfaced

  @TS-021 @FR-003 @P2 @validation
  Scenario: Conflict detection scope is numeric-token divergence within a canonical_key group only
    Given two claims sharing the same canonical_key
    And both claims carry string-valued fields that disagree categorically
    And neither claim carries a numeric_token field that disagrees
    When the aggregator inspects the canonical_key group
    Then zero ConflictSet entries are produced for the group
    And the aggregation_report.json artifact records a deferred_categorical_conflicts count that increments by one
    And no silent reconciliation of the categorical disagreement occurs

  @TS-022 @FR-003 @P2 @validation
  Scenario Outline: Numeric-token divergence within a canonical_key group raises a conflict
    Given two claims sharing canonical_key "<key>"
    And claim_a carries numeric_token "<a>"
    And claim_b carries numeric_token "<b>"
    When the aggregator inspects the canonical_key group
    Then exactly one ConflictSet is produced for "<key>"
    And the ConflictSet preserves claim_a and claim_b verbatim

    Examples:
      | key          | a       | b       |
      | total_usd    | 1250.00 | 1275.50 |
      | count        | 12      | 14      |
      | rate_bps     | 15      | 25      |
