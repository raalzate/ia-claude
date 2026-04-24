# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Team Rules Win Over Personal Preferences on Project Tasks
  Project-scope memory takes precedence over user-scope memory for project tasks; personal rules must never pollute team behavior.

  Background:
    Given a project memory file ".claude/CLAUDE.md" declaring team rules
    And a personal memory file "~/.claude/CLAUDE.md" declaring personal rules
    And the resolver loads both scopes with labels "team" and "personal"

  @TS-005 @FR-006 @SC-002 @P2 @acceptance
  Scenario: Team pnpm rule overrides conflicting personal npm rule on project task
    Given a team rule with key "package-manager" in project memory
    And a personal rule with key "package-manager" in user memory
    When the effective memory for a project task is computed
    Then the team entry is retained in the effective view
    And the personal entry for "package-manager" is dropped from the effective view

  @TS-006 @FR-003 @SC-002 @P2 @acceptance
  Scenario: Dropped personal rule is recorded as a non-fatal diagnostic
    Given a team rule and a personal rule collide on rule key "indent-style"
    When the effective memory for a project task is computed
    Then a ResolutionDiagnostic of kind "personal_overridden_by_team" is appended to diagnostics
    And the diagnostic carries conflicting_rule_key equal to "indent-style"
    And the diagnostic severity is "info"

  @TS-007 @FR-003 @FR-006 @SC-002 @P2 @acceptance
  Scenario: Non-conflicting personal preference is respected in effective memory
    Given a personal rule with key "editor-theme" that does not collide with any team rule key
    When the effective memory for a project task is computed
    Then the personal entry for "editor-theme" is retained in the effective view
    And no diagnostic of kind "personal_overridden_by_team" is emitted for key "editor-theme"

  @TS-008 @FR-003 @SC-002 @P2 @acceptance
  Scenario Outline: Every conflicting personal rule is dropped in favor of the team rule
    Given a team rule with key "<rule_key>" in project memory
    And a personal rule with key "<rule_key>" in user memory
    When the effective memory for a project task is computed
    Then the team entry wins for key "<rule_key>"
    And the conflict test matrix records zero personal rules reaching agent output

    Examples:
      | rule_key         |
      | package-manager  |
      | indent-style     |
      | commit-format    |
      | test-runner      |

  @TS-009 @FR-003 @P2 @acceptance
  Scenario: Personal memory file lives outside version control
    Given the personal memory file is located under the user's HOME directory
    When the repository's tracked files are enumerated
    Then the personal memory file is not part of the repository
    And the resolver never writes to the personal memory file
