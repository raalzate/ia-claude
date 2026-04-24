# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Testing Rules Auto-Inject on Matching Edits
  Rule files in .claude/rules/ must activate automatically and exclusively when at least one edited file in a turn matches a declared paths glob.

  Background:
    Given a .claude/rules/ directory exists
    And a rule file "testing.md" declares paths ["**/*.test.tsx"] in its YAML frontmatter
    And the rule file's frontmatter is otherwise valid

  @TS-001 @FR-001 @SC-002 @P1 @acceptance
  Scenario: Matching edit injects the single declared rule file
    Given no other rule files declare a pattern matching "src/components/Button.test.tsx"
    When the practitioner edits "src/components/Button.test.tsx"
    Then the active rule set for the turn contains exactly "testing.md"
    And the activation audit log records "testing.md" with edited path "src/components/Button.test.tsx"

  @TS-002 @FR-001 @FR-005 @SC-002 @SC-004 @P1 @acceptance
  Scenario: Only the matching rule file is injected when multiple rule files exist
    Given additional rule files "api-conventions.md" and "styles.md" declare non-matching patterns
    When the practitioner edits a single file "src/components/Button.test.tsx"
    Then the active rule set contains exactly one rule file "testing.md"
    And the activation audit log lists exactly one activation
    And "api-conventions.md" does not appear in the active rule set
    And "styles.md" does not appear in the active rule set

  @TS-003 @FR-001 @FR-005 @SC-004 @P1 @acceptance
  Scenario Outline: Matching edits trigger activation audit entries
    When the practitioner edits "<edited_path>"
    Then the active rule set contains "testing.md"
    And the activation audit log records edited path "<edited_path>" triggering "testing.md" via pattern "**/*.test.tsx"

    Examples:
      | edited_path                          |
      | src/components/Button.test.tsx       |
      | tests/unit/Foo.test.tsx              |
      | packages/ui/src/Modal.test.tsx       |

  @TS-004 @FR-005 @SC-004 @P1 @acceptance
  Scenario: Multiple edits matching the same rule yield one member and multiple events
    When the practitioner edits "src/components/Button.test.tsx" and "src/components/Card.test.tsx" in one turn
    Then the active rule set contains "testing.md" exactly once
    And the activation audit log contains one MatchingEvent per edited path
    And each event references pattern "**/*.test.tsx"

  @TS-005 @FR-005 @P1 @contract
  Scenario: Activation audit records conform to rule-activation-event schema
    When the practitioner edits "src/components/Button.test.tsx"
    Then each emitted activation record validates against contracts/rule-activation-event.schema.json
    And each record carries turn_id, edited_path, activated_rules, and timestamp fields
