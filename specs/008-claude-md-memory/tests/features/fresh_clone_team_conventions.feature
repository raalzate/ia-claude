# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Zero-Setup Team Conventions on Fresh Clone
  A fresh clone must yield identical, deterministic team memory for every agent session with no per-user configuration.

  Background:
    Given a fresh clone of the repository at a known commit SHA
    And no user-level memory overriding team rules
    And the project memory file ".claude/CLAUDE.md" is present at the repo root

  @TS-001 @FR-001 @SC-001 @P1 @acceptance
  Scenario: Agent startup loads project memory without per-user configuration
    When the practitioner starts an agent session in the repo root
    Then the resolver loads the project memory file at startup
    And the resolver treats project memory as authoritative for project work
    And no per-user configuration step is required to produce the loaded memory

  @TS-002 @FR-002 @SC-001 @P1 @acceptance
  Scenario: @path reference into standards manual is resolved into effective memory
    Given the project memory file contains a reference "@./standards/coding-style.md"
    And the referenced manual exists on disk
    When the resolver resolves the project memory file
    Then the referenced manual content is pulled into the effective memory
    And the aggregated memory contains one MemoryEntry whose source_path matches the referenced manual

  @TS-003 @FR-005 @SC-001 @P1 @acceptance
  Scenario: Two independent clones at the same commit produce byte-identical ResolvedMemory
    Given two independent clones of the repository at the same commit SHA
    When each clone runs the resolver on its project memory file
    Then both runs produce ResolvedMemory objects whose JSON serialization is byte-identical
    And the declaration_order of every entry matches across both runs

  @TS-004 @FR-005 @SC-001 @P1 @contract
  Scenario: ResolvedMemory conforms to the declared JSON schema
    Given a ResolvedMemory produced by the resolver
    When the object is validated against contracts/resolved-memory.schema.json
    Then validation passes
    And every MemoryEntry carries source_path, source_sha256, and declaration_order fields
