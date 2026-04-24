# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Automated Inline Review on Every Pull Request
  A pull request triggers a non-interactive Claude Code CLI invocation whose structured output becomes inline annotations without manual intervention.

  Background:
    Given a pull request opened against the workshop repository
    And the CI workflow is configured to invoke the Claude Code CLI
    And a GITHUB_TOKEN is available to the CI job

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: CLI runs non-interactively with the --print flag
    Given the pull request has at least one changed file
    When the CI workflow triggers the reviewer step
    Then the Claude Code CLI is invoked with the "--print" flag
    And no TTY or interactive prompt is attached to the CLI process
    And the CLI process completes without requesting human input

  @TS-002 @FR-002 @SC-001 @P1 @acceptance
  Scenario: CLI invocation declares structured output contract
    Given the pull request has at least one changed file
    When the CI workflow invokes the Claude Code CLI
    Then the invocation passes "--output-format json"
    And the invocation passes "--json-schema" referencing the declared envelope schema

  @TS-003 @FR-005 @SC-003 @P1 @acceptance
  Scenario: Validated findings become inline annotations on the PR diff
    Given the reviewer emits a schema-valid envelope with at least one finding
    When the CI step that maps findings runs
    Then each finding is posted as an inline annotation on the pull request
    And each annotation is attached to the file path and line reported in the finding
    And no manual action was required between "push" and "annotation visible"

  @TS-004 @FR-005 @P1 @acceptance
  Scenario Outline: Severity maps deterministically to annotation_level
    Given a schema-valid finding with severity "<severity>"
    When the mapper posts it to the Checks API
    Then the annotation_level is "<level>"

    Examples:
      | severity | level   |
      | info     | notice  |
      | warning  | warning |
      | error    | failure |
