# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Zero Rule Tokens on Unrelated Edits
  Turns that edit no files matched by any declared path pattern must inject zero rule files and add zero bytes of rule context, defending against the always-on rule loading anti-pattern.

  Background:
    Given a .claude/rules/ directory contains rule files with declared paths patterns
    And a baseline prompt byte size is measured with no rule files loaded
    And no domain-specific heuristics are placed in the host repo CLAUDE.md

  @TS-006 @FR-002 @FR-006 @SC-001 @P2 @acceptance
  Scenario: Unmatched edit produces zero activations
    Given no rule file declares a pattern that matches "README.md"
    When the practitioner edits "README.md"
    Then the active rule set is empty
    And the activation audit log shows zero activations for that turn

  @TS-007 @FR-002 @FR-006 @SC-001 @P2 @acceptance
  Scenario: Zero-activation turn adds zero rule bytes to the prompt
    Given no rule file declares a pattern matching the turn's edited paths
    When the practitioner edits "docs/architecture.md"
    Then the composed prompt byte size equals the baseline byte size
    And total_body_bytes for the active rule set is 0

  @TS-008 @FR-002 @P2 @acceptance
  Scenario: Read-only operation touching no file triggers no activation
    Given the practitioner performs a read-only tool call that edits no file
    When the turn completes
    Then no rule file is injected
    And the active rule set contains zero members
    And the activation audit log shows zero activations

  @TS-009 @FR-006 @SC-001 @P2 @acceptance
  Scenario Outline: Rule files whose patterns match nothing this turn are inert
    Given a rule file declares paths ["<inert_pattern>"]
    When the practitioner edits only "<unrelated_path>"
    Then the rule file contributes zero bytes to the prompt
    And the active rule set does not contain that rule file

    Examples:
      | inert_pattern         | unrelated_path          |
      | src/api/**/*.ts       | README.md               |
      | **/*.test.tsx         | src/utils/helpers.ts    |
      | docs/**/*.md          | src/index.ts            |

  @TS-010 @FR-007 @P2 @acceptance
  Scenario: Domain-specific heuristics must not live in global CLAUDE.md
    Given the host repository CLAUDE.md file is inspected
    When the contract test scans for domain-specific rules
    Then no narrowly-scoped domain heuristic appears in CLAUDE.md
    And all domain-specific rules live only under .claude/rules/

  @TS-011 @FR-002 @SC-001 @P2 @validation
  Scenario: Adding new rule files does not change token cost for unmatched turns
    Given a baseline turn token cost is recorded for editing "README.md"
    When three additional rule files are added to .claude/rules/ with non-matching patterns
    And the practitioner edits "README.md" again
    Then the new turn token cost equals the baseline within a small measurement tolerance
