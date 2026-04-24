# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Team Memory Size Budget Enforces Context Economy
  Aggregated team memory must stay under a declared byte budget so modular @path splits replace inline bloat.

  @TS-019 @FR-007 @SC-003 @P1 @acceptance
  Scenario: Aggregated team memory within budget resolves successfully
    Given a valid fixture whose aggregated team memory is under TEAM_MEMORY_MAX_BYTES
    When the resolver resolves the project memory file
    Then a ResolvedMemory is returned
    And team_bytes_total is less than or equal to team_bytes_budget
    And team_bytes_budget equals the declared TEAM_MEMORY_MAX_BYTES constant

  @TS-020 @FR-007 @SC-003 @P1 @acceptance
  Scenario: Aggregated team memory over budget raises OversizeMemoryError
    Given a fixture whose aggregated team memory strictly exceeds TEAM_MEMORY_MAX_BYTES
    When the resolver resolves the project memory file
    Then an OversizeMemoryError is raised before ResolvedMemory is constructed
    And the exception carries a ResolutionDiagnostic of kind "oversize_memory"
    And the diagnostic records bytes_observed and bytes_budget fields

  @TS-021 @FR-007 @SC-003 @P1 @acceptance
  Scenario: Only team-scope entries count against the size budget
    Given team entries totalling B_team bytes
    And personal entries totalling B_personal bytes
    When the resolver resolves the project memory file
    Then team_bytes_total equals B_team
    And personal-scope bytes are excluded from the size budget accounting

  @TS-022 @FR-007 @SC-003 @P1 @validation
  Scenario: The top-level CLAUDE.md relies on @path modularization rather than inline bloat
    Given the canonical project memory template shipped by this kata
    When the top-level file size is measured
    Then the top-level file size is well below TEAM_MEMORY_MAX_BYTES
    And the majority of effective memory volume is delivered via @path-referenced manuals
