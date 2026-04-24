# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Fail-Loud Diagnostics for Missing, Unreadable, and Circular References
  Every unresolvable @path reference must raise an explicit typed diagnostic; silent degradation is prohibited.

  Background:
    Given a project memory file ".claude/CLAUDE.md" is loaded by the resolver
    And the resolver emits typed exceptions carrying a ResolutionDiagnostic
    And no silent best-effort fallback path exists

  @TS-014 @FR-004 @SC-004 @P1 @acceptance
  Scenario: Missing @path target raises MissingReferenceError with diagnostic
    Given the project memory file references "@./standards/ghost.md"
    And the referenced file does not exist on disk
    When the resolver resolves the project memory file
    Then a MissingReferenceError is raised
    And the exception carries a ResolutionDiagnostic of kind "missing_target"
    And the diagnostic reference field identifies the offending PathReference

  @TS-015 @FR-004 @P1 @acceptance
  Scenario: Circular @path chain raises CircularReferenceError with cycle path
    Given the project memory file references "@./a.md"
    And "a.md" references "@./b.md"
    And "b.md" references "@./a.md"
    When the resolver resolves the project memory file
    Then a CircularReferenceError is raised
    And the exception carries a ResolutionDiagnostic of kind "circular_reference"
    And the cycle_path field lists the ordered absolute paths forming the cycle
    And the cycle_path is closed so that the first element equals the last element

  @TS-016 @FR-004 @P1 @acceptance
  Scenario: Unreadable @path target raises UnreadableReferenceError
    Given the project memory file references a file whose permissions deny read access
    When the resolver resolves the project memory file
    Then an UnreadableReferenceError is raised
    And the exception carries a ResolutionDiagnostic of kind "unreadable_target"
    And the diagnostic severity is "error"

  @TS-017 @FR-004 @SC-004 @P1 @acceptance
  Scenario Outline: Fatal diagnostic kinds raise typed exceptions 100 percent of the time
    Given a fixture tree that triggers a "<kind>" condition
    When the resolver resolves the project memory file in that fixture tree
    Then the resolver raises an exception of type "<exception>"
    And the raised exception carries a ResolutionDiagnostic of kind "<kind>"
    And no partially-resolved ResolvedMemory object is returned

    Examples:
      | kind               | exception                 |
      | missing_target     | MissingReferenceError     |
      | circular_reference | CircularReferenceError    |
      | unreadable_target  | UnreadableReferenceError  |
      | oversize_memory    | OversizeMemoryError       |

  @TS-018 @FR-004 @P1 @contract
  Scenario: ResolutionDiagnostic records conform to the declared JSON schema
    Given a ResolutionDiagnostic emitted by the resolver
    When the diagnostic is validated against contracts/resolution-diagnostic.schema.json
    Then validation passes
    And the diagnostic kind is one of the closed enum values declared in the schema
