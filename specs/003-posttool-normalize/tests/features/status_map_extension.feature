# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Status Map Extension Is a Pure Data Change
  Adding a new arcane status code mapping requires touching only the normalization map — no prompts, no model settings, no agent wiring.

  @TS-020 @FR-003 @SC-003 @US-003 @P3 @acceptance
  Scenario: New status code added to the map resolves in the normalized JSON
    Given a tool response emitting an arcane status code not previously mapped
    When a single entry mapping that code to a human-readable label is added to the StatusMapping
    And the tool response is replayed through the hook
    Then the status.code field of the appended message carries the newly added label
    And the status.raw field is null

  @TS-021 @FR-003 @US-003 @P3 @acceptance
  Scenario: Extension diff modifies only the normalization map
    Given a status code was added to the StatusMapping
    When the practitioner diffs the change against the prior commit
    Then only the normalization map module is modified
    And no prompts, model settings, or agent wiring files appear in the diff

  @TS-022 @FR-003 @FR-006 @US-003 @P3 @acceptance
  Scenario: Previously-unknown code transitions from "unknown" marker to resolved label
    Given a baseline run where the arcane code normalized to status.code "unknown" with the raw code preserved
    When the StatusMapping is extended with that code mapped to a human-readable label
    And the same fixture is replayed
    Then the same payload now normalizes to status.code equal to the added label
    And status.raw is null in the new run
