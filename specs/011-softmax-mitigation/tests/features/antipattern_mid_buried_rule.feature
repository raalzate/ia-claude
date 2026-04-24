# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Anti-Pattern Demonstration of Rule Buried in the Middle
  Prove the softmax-dilution effect on the practitioner's workload by rendering the same rule in the
  middle of the prompt and measuring the compliance drop versus the edge-placed baseline.

  @TS-010 @FR-006 @FR-007 @SC-002 @P2 @acceptance
  Scenario: Mid-placement run drops compliance by at least 20 percentage points versus edge placement
    Given an edge-placed baseline compliance rate recorded for the same critical rule and adversarial batch
    And a PromptLayout rendered with label "mid_buried" and allow_anti_pattern True
    When the same adversarial request batch is executed against the mid_buried layout
    Then the observed compliance rate drops by at least 20 percentage points versus the edge-placed baseline
    And the delta is recorded against PromptLayout.min_delta_pct for audit

  @TS-011 @FR-004 @FR-007 @P2 @acceptance
  Scenario: Anti-pattern report attributes violations to mid-context burying
    Given a completed mid-placement run
    When the practitioner reviews the run output
    Then a clearly labelled anti-pattern report is produced
    And the report names each violating trial by ComplianceRecord.trial_id
    And the report attributes the violations to mid-context burying of the critical rule

  @TS-012 @FR-006 @P2 @validation
  Scenario: Rendering a mid_buried layout without the opt-in flag is refused
    Given a PromptBuilder request for label "mid_buried" with allow_anti_pattern False
    When the builder attempts to construct the layout
    Then construction raises an AntiPatternNotAuthorized exception
    And no PromptLayout instance is returned

  @TS-013 @FR-006 @P2 @validation
  Scenario: Mid-buried layout keeps both edge regions empty of critical rules
    Given a PromptLayout rendered with label "mid_buried" and allow_anti_pattern True
    When the layout is inspected
    Then primacy_region.placed_rule_ids is empty
    And latency_region.placed_rule_ids is empty
    And the critical rule text appears only inside the mid-body portion of rendered_prompt

  @TS-014 @FR-007 @SC-002 @P2 @contract
  Scenario: Mid_buried layout carries a declared min_delta_pct for audit
    Given a PromptLayout with label "mid_buried"
    When the instance is serialized and validated against contracts/prompt-layout.schema.json
    Then the payload passes schema validation
    And min_delta_pct is present and at least 20
    And compliance_target_pct is present and at most 100
