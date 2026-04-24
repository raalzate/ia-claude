# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Editing a Referenced Manual Updates Agent Behavior Without Touching CLAUDE.md
  The @path reference is a live pointer, not a snapshot — edits to referenced manuals flow into the next session without modifying CLAUDE.md.

  @TS-010 @FR-002 @SC-001 @P3 @acceptance
  Scenario: Updated standards manual takes effect on the next resolver run
    Given the project memory file references "@./standards/coding-style.md"
    And the referenced manual is updated with a new rule
    And the project memory file itself is unchanged
    When the resolver is run again on the project memory file
    Then the new rule appears in the MemoryEntry for the referenced manual
    And the source_sha256 of that entry reflects the updated file contents

  @TS-011 @FR-002 @P3 @acceptance
  Scenario: Removed @path reference drops rules that only lived in the referenced manual
    Given the project memory file previously referenced "@./standards/coding-style.md"
    And the reference is removed from the project memory file
    When the resolver is run on the updated project memory file
    Then no MemoryEntry is produced for the dereferenced manual
    And rules that only existed in that manual are absent from the effective memory

  @TS-012 @FR-002 @FR-005 @P3 @contract
  Scenario: PathReference entries conform to the declared JSON schema
    Given a resolver run that produced at least one PathReference
    When each PathReference is validated against contracts/path-reference.schema.json
    Then validation passes for every reference
    And each reference carries raw, resolved_path, parent_path, declaration_line, and scope fields

  @TS-013 @FR-002 @P3 @acceptance
  Scenario: Diamond-shaped @path graph produces exactly one MemoryEntry per unique file
    Given two files both reference "@./standards/shared.md"
    When the resolver resolves the project memory file
    Then exactly one MemoryEntry is produced for "standards/shared.md"
    And a ResolutionDiagnostic of kind "duplicate_reference" is recorded for the second visit
    And the duplicate diagnostic has severity "warning"
