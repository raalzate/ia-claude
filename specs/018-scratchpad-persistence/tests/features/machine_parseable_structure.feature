# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Machine-Parseable Scratchpad Structure
  The scratchpad is a declared, sectioned, schema-enforced document — never an unstructured prose blob.

  @TS-012 @FR-002 @FR-010 @SC-002 @US-003 @P3 @acceptance
  Scenario: Every finding maps to exactly one declared section with required fields
    Given a populated scratchpad produced by a real investigation
    When the structure validator parses the file
    Then 100% of findings are located under a declared section
    And every finding exposes id, timestamp, category, evidence, and source_ref fields
    And no finding lives outside the declared fixed section list

  @TS-013 @FR-010 @US-003 @P3 @acceptance
  Scenario: Sections are visually delimited and findings are individually identifiable
    Given a practitioner opens the scratchpad in a text viewer
    When they scan the file
    Then declared sections are clearly delimited by their declared headers
    And each finding is individually identifiable rather than merged into prose

  @TS-014 @FR-006 @FR-010 @SC-002 @US-003 @P3 @acceptance
  Scenario: Write of a finding missing required metadata is rejected or flagged
    Given a finding payload missing a required metadata field
    When the writer attempts to persist it
    Then the write is rejected with a ScratchpadSchemaError
    And the scratchpad file on disk is left untouched

  @TS-015 @FR-002 @FR-010 @US-003 @P3 @contract
  Scenario: Scratchpad document validates against the declared JSON schema
    Given a scratchpad file rendered from a parsed Scratchpad model
    When the document is validated against contracts/scratchpad-document.schema.json
    Then validation passes
    And every embedded finding validates against contracts/finding.schema.json

  @TS-016 @FR-002 @FR-010 @US-003 @P3 @validation
  Scenario Outline: Structural drift in the scratchpad fails loud with ScratchpadSchemaError
    Given a scratchpad file on disk containing "<drift_kind>"
    When the structure validator parses the file
    Then a ScratchpadSchemaError is raised
    And the error payload reports the byte offset of the failure
    And no fallback text-search classification is attempted

    Examples:
      | drift_kind                              |
      | unknown section name                    |
      | finding missing required id field       |
      | finding missing required timestamp      |
      | prose blob outside any declared section |

  @TS-017 @FR-005 @SC-004 @US-003 @P3 @acceptance
  Scenario: Reaching MAX_SCRATCHPAD_BYTES triggers a rotation event and preserves prior content
    Given the active scratchpad is within 1 write of MAX_SCRATCHPAD_BYTES
    When the next finding causes the rendered size to exceed the cap
    Then a RotationEvent is emitted to rotation.jsonl
    And the prior scratchpad is archived to "<name>.<iso-date>.md"
    And a fresh active scratchpad is created with a prior-pad anchor block
    And the active scratchpad size never exceeds MAX_SCRATCHPAD_BYTES

  @TS-018 @FR-005 @US-003 @P3 @contract
  Scenario: RotationEvent conforms to the declared JSON schema
    Given a RotationEvent produced by a rotation
    When it is validated against contracts/rotation-event.schema.json
    Then validation passes
    And the event carries event_id, rotated_from, rotated_to, size_at_rotation, and rotated_at fields

  @TS-019 @FR-009 @SC-001 @US-003 @P3 @contract
  Scenario: ContextAnchor seeded into a resumed session conforms to the declared JSON schema
    Given a ContextAnchor emitted by the compaction bridge
    When it is validated against contracts/context-anchor.schema.json
    Then validation passes
    And the anchor carries decisions_snapshot, open_questions_snapshot, map_summary, and source_pad_id fields
