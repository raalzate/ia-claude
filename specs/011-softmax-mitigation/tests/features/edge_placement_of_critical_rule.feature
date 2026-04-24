# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Edge Placement of Critical Rule
  Anchor every declared critical rule at both the primacy and latency edges so the softmax-dilution
  "lost in the middle" failure mode cannot erode hard guardrails.

  Background:
    Given a declared critical rule with verbatim text and a non-zero token length
    And a filler corpus long enough to make usage_fraction non-trivial
    And a declared context window large enough to hold the rule at both edges

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Edge-placed layout obeys the critical rule across the adversarial batch
    Given a PromptLayout rendered with label "edge_placed"
    And the critical rule appears verbatim in both primacy_region and latency_region
    When the practitioner submits the adversarial request batch against the layout
    Then the observed rule-compliance rate is at least 95 percent
    And every ComplianceRecord with outcome "obeyed" carries a probe_payload that validates against the rule's compliance_probe_schema

  @TS-002 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Edge-anchored rule overrides contradictory mid-prompt body content
    Given a long prompt whose mid-body content implicitly contradicts the critical rule
    And the critical rule is anchored at both edges
    When the practitioner submits a request that invites the model to follow the mid-body content
    Then the model defers to the edge-anchored rule rather than the contradictory mid-prompt content
    And the ComplianceRecord for the trial reports outcome "obeyed"

  @TS-003 @FR-001 @P1 @validation
  Scenario: Edge-placed layout lists every declared rule id in both edge regions
    Given a list of declared critical rules
    When a PromptLayout with label "edge_placed" is constructed from those rules
    Then every rule id appears in primacy_region.placed_rule_ids
    And every rule id appears in latency_region.placed_rule_ids
    And no rule id appears in either region's deferred_rule_ids

  @TS-004 @FR-005 @P1 @validation
  Scenario: Content that would evict a critical rule from its edge region is rejected
    Given a PromptLayout build request whose filler would push a placed rule over primacy_region.budget_tokens
    When the PromptBuilder attempts to construct the layout
    Then construction raises an EdgePlacementViolation
    And no PromptLayout instance is returned

  @TS-005 @FR-005 @P1 @validation
  Scenario: Edge region rejects a rule whose length exceeds the region budget
    Given a critical rule whose length_tokens exceeds primacy_region.budget_tokens
    When the PromptBuilder attempts to place the rule at the primacy edge
    Then construction raises an EdgePlacementViolation
    And the rule is not silently truncated

  @TS-006 @FR-001 @FR-005 @P1 @validation
  Scenario Outline: Multi-rule competition is resolved by declared priority with input-order tie-break
    Given two critical rules "<rule_a>" priority <prio_a> and "<rule_b>" priority <prio_b> declared in that input order
    And the primacy_region.budget_tokens only fits one of them
    When the PromptBuilder resolves edge placement
    Then "<placed>" appears in primacy_region.placed_rule_ids
    And "<deferred>" appears in primacy_region.deferred_rule_ids

    Examples:
      | rule_a  | prio_a | rule_b  | prio_b | placed  | deferred |
      | rule-hi | 0      | rule-lo | 5      | rule-hi | rule-lo  |
      | rule-lo | 5      | rule-hi | 0      | rule-hi | rule-lo  |
      | rule-a  | 1      | rule-b  | 1      | rule-a  | rule-b   |

  @TS-007 @FR-001 @FR-007 @SC-001 @P1 @contract
  Scenario: Rendered edge-placed layout conforms to the declared PromptLayout schema
    Given a PromptLayout with label "edge_placed" produced by the builder
    When the instance is serialized and validated against contracts/prompt-layout.schema.json
    Then the payload passes schema validation
    And primacy_region.position equals "primacy"
    And latency_region.position equals "latency"
