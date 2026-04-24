# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: New Rule File Activates Only on Matching Edits
  Adding a new rule file with a new path pattern must activate automatically on matching edits and remain dormant on non-matching edits, without code changes or agent restart.

  Background:
    Given a new rule file ".claude/rules/api-conventions.md" is added
    And its YAML frontmatter declares paths ["src/api/**/*.ts"]
    And no agent restart or CLAUDE.md edit is performed

  @TS-012 @FR-001 @SC-002 @P3 @acceptance
  Scenario: New rule file activates on a matching edit
    When the practitioner edits "src/api/users.ts"
    Then "api-conventions.md" is injected into the active rule set
    And the activation audit log records "api-conventions.md" with edited path "src/api/users.ts"

  @TS-013 @FR-002 @P3 @acceptance
  Scenario: New rule file stays dormant on a non-matching edit
    When the practitioner edits "src/components/Button.tsx"
    Then "api-conventions.md" is NOT injected
    And the active rule set does not contain "api-conventions.md"

  @TS-014 @FR-004 @P3 @acceptance
  Scenario: Overlapping patterns resolve deterministically by precedence then filename
    Given rule file "a-rules.md" declares paths ["src/**/*.ts"] with precedence 50
    And rule file "b-rules.md" declares paths ["src/**/*.ts"] with precedence 100
    And rule file "c-rules.md" declares paths ["src/**/*.ts"] with precedence 100
    When the practitioner edits "src/api/users.ts"
    Then the active rule set members are ordered "a-rules.md" then "b-rules.md" then "c-rules.md"
    And two runs over the same edits produce the same activation set in the same order

  @TS-015 @FR-003 @SC-003 @P3 @acceptance
  Scenario Outline: Invalid frontmatter produces an explicit load-time error
    Given a rule file ".claude/rules/broken.md" with "<defect>"
    When the loader attempts to load rule files
    Then a FrontmatterError is raised identifying "broken.md"
    And the error reason is "<reason>"
    And no silent skip occurs

    Examples:
      | defect                                  | reason                |
      | malformed YAML frontmatter              | yaml_parse_error      |
      | frontmatter missing the paths key       | missing_paths_key     |
      | paths value is a scalar not a list      | paths_not_list        |
      | paths value is an empty list            | paths_empty           |
      | a paths list entry is an empty string   | empty_glob            |
      | precedence value is not an integer      | precedence_not_int    |
      | file lacks the opening frontmatter fence| no_frontmatter_fence  |

  @TS-016 @FR-003 @P3 @contract
  Scenario: Loader diagnostics conform to the loader-diagnostic schema
    Given a rule file with invalid frontmatter is present
    When the loader emits a diagnostic
    Then the diagnostic validates against contracts/loader-diagnostic.schema.json
    And it carries severity, code, source_file, and message fields

  @TS-017 @FR-003 @P3 @contract
  Scenario: Rule file frontmatter conforms to the frontmatter schema
    Given a valid rule file is loaded
    When its parsed frontmatter is validated
    Then the frontmatter validates against contracts/rule-file-frontmatter.schema.json
    And the paths array contains at least one non-empty glob string

  @TS-018 @FR-005 @SC-004 @P3 @acceptance
  Scenario: Multiple matching files in one turn activate all corresponding rule files deduplicated
    Given rule file "testing.md" declares paths ["**/*.test.tsx"]
    And rule file "api-conventions.md" declares paths ["src/api/**/*.ts"]
    When the practitioner edits "src/components/Button.test.tsx" and "src/api/users.ts" in one turn
    Then the active rule set contains both "testing.md" and "api-conventions.md"
    And each rule file appears exactly once in the active rule set
    And the activation audit log lists every matching (edited_path, rule_file) pair

  @TS-019 @FR-005 @P3 @validation
  Scenario: Very large rule file still appears in the activation audit log
    Given a matching rule file body_byte_size exceeds the large-rule threshold
    When the practitioner edits a matching file
    Then the rule file appears in the active rule set
    And the activation audit log records the activation
    And a "large_rule_body" or "oversized_rule_file" diagnostic is surfaced
