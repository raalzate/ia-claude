# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Proactive Compaction and Re-Anchoring
  Fire a compaction event inside the 55 to 60 percent capacity band, summarise older turns, and re-render
  the prompt with every declared critical rule verbatim at both edges before attention rot sets in.

  Background:
    Given a declared list of critical rules with stable ids and verbatim content
    And a declared context_window_tokens value for the target model
    And an active session whose PromptLayout label is "edge_placed_with_compaction"

  @TS-020 @FR-002 @SC-003 @P3 @acceptance
  Scenario: Compaction fires before usage exceeds 60 percent
    Given the session's usage_fraction crosses into the 50 to 60 percent compaction band
    When the next turn is prepared
    Then a CompactionEvent is emitted before usage_fraction exceeds 0.60
    And the event's fired_at_usage_fraction lies in the half-open interval [0.55, 0.60)

  @TS-021 @FR-002 @FR-005 @SC-003 @P3 @validation
  Scenario Outline: CompactionTrigger decision is a step function of usage fraction
    Given a CompactionTrigger configured with the declared 55 to 60 percent band
    When the trigger is evaluated at usage_fraction <usage>
    Then the fire decision equals <should_fire>

    Examples:
      | usage | should_fire |
      | 0.49  | false       |
      | 0.55  | true        |
      | 0.59  | true        |
      | 0.60  | true        |
      | 0.61  | true        |

  @TS-022 @FR-002 @SC-003 @P3 @validation
  Scenario: Trigger failing to fire before 60 percent raises CompactionOverdue
    Given a session whose usage_fraction has reached 0.61 without any prior CompactionEvent
    When the next turn is prepared
    Then a CompactionOverdue exception is raised
    And the session refuses to dispatch the turn

  @TS-023 @FR-003 @SC-004 @P3 @acceptance
  Scenario: Post-compaction prompt re-anchors every critical rule verbatim at both edges
    Given a CompactionEvent has just completed for the session
    When the post-compaction PromptLayout is rendered
    Then every declared critical rule appears verbatim in primacy_region.placed_rule_ids
    And every declared critical rule appears verbatim in latency_region.placed_rule_ids
    And the verbatim rule content is byte-identical to the pre-compaction rule content

  @TS-024 @FR-003 @SC-004 @P3 @validation
  Scenario: CompactionEvent with any rule missing after re-anchoring is rejected
    Given a CompactionEvent candidate whose rules_missing_after list is non-empty
    When the event is constructed
    Then a RuleMissingAfterCompaction exception is raised
    And no CompactionEvent instance is persisted

  @TS-025 @FR-002 @FR-003 @SC-001 @P3 @acceptance
  Scenario: Replaying the adversarial batch against the compacted session preserves compliance
    Given a pre-compaction edge-placed compliance rate recorded for the adversarial batch
    And a CompactionEvent has just completed and re-anchored every rule at both edges
    When the same adversarial batch is replayed against the post-compaction prompt
    Then the post-compaction compliance rate is not materially lower than the pre-compaction rate
    And the post-compaction compliance rate remains at least 95 percent

  @TS-026 @FR-004 @P3 @contract
  Scenario: CompactionEvent record conforms to the declared schema and carries audit fields
    Given a CompactionEvent emitted by a session
    When the instance is serialized and validated against contracts/compaction-event.schema.json
    Then the payload passes schema validation
    And the record carries event_id, session_id, fired_at_usage_fraction, collapsed_turn_count, and rules_preserved
    And rules_missing_after is an empty list

  @TS-027 @FR-004 @FR-007 @P3 @contract
  Scenario: ComplianceRecord rows conform to the declared schema for every trial
    Given a completed compliance sweep that covers edge_placed, mid_buried, and edge_placed_with_compaction layouts
    When each ComplianceRecord is validated against contracts/compliance-record.schema.json
    Then every record passes schema validation
    And every record carries trial_id, layout_label, rule_id, outcome, and prompt_hash
    And every record with outcome "obeyed" carries a non-null probe_payload
