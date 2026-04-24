# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Transactional Persistence of Findings at Moment of Discovery
  Every critical finding must be appended to the declared scratchpad file the moment it is made so no context event can erase it.

  Background:
    Given a declared scratchpad path under the session run directory
    And the declared fixed sections "map", "findings", "open_questions", "decisions", "conflicts"
    And a ScratchpadWriter bound to that path

  @TS-001 @FR-001 @FR-002 @SC-002 @US-001 @P1 @acceptance
  Scenario: First finding in a fresh session creates the scratchpad with declared structure
    Given no scratchpad file exists at the declared path
    When the agent records its first critical finding under section "findings"
    Then the scratchpad file is created at the declared path
    And the file exposes all declared fixed sections
    And the finding is written into the "findings" section

  @TS-002 @FR-001 @FR-002 @US-001 @P1 @acceptance
  Scenario: New finding is appended without modifying prior entries
    Given a scratchpad already contains 3 findings under section "findings"
    When the agent records a new finding under section "findings"
    Then the new finding is appended after the existing 3 findings
    And none of the existing 3 findings are modified, reordered, or removed

  @TS-003 @FR-001 @FR-008 @US-001 @P1 @acceptance
  Scenario: Session terminated without explicit save still has every acknowledged finding on disk
    Given the agent has acknowledged 3 findings during the session
    When the session is terminated abruptly with no explicit save action
    Then all 3 acknowledged findings are present on disk in their declared sections
    And no finding is lost due to missing end-of-session batching

  @TS-004 @FR-001 @FR-006 @SC-002 @US-001 @P1 @acceptance
  Scenario Outline: Each finding carries the metadata required by the declared schema
    When the agent records a finding with category "<category>" and evidence "<evidence>"
    Then the persisted finding exposes a stable id
    And the persisted finding exposes a UTC timestamp
    And the persisted finding exposes the category "<category>"
    And the persisted finding exposes a source_ref field
    And the finding is routed to the section mapped to category "<category>"

    Examples:
      | category     | evidence                               |
      | architecture | module X hosts the router              |
      | data         | users.csv drives the profile fixture   |
      | bug          | null deref in handler Y                |
      | decision     | adopt pydantic v2 for schemas          |
      | question     | is cache invalidation session-scoped?  |

  @TS-005 @FR-008 @US-001 @P1 @acceptance
  Scenario: Atomic write survives mid-write process termination
    Given the writer begins persisting a finding
    When the process is terminated during the write
    Then the scratchpad file on disk is parseable
    And the finding is either fully present or fully absent, never partial

  @TS-006 @FR-008 @US-001 @P1 @acceptance
  Scenario: Concurrent writers serialise through the file lock
    Given two independent ScratchpadWriter instances bound to the same path
    When both attempt to append a finding at the same time
    Then the writes are serialised by the POSIX file lock
    And the resulting scratchpad contains both findings in a single well-formed document
    And neither write produces interleaved or corrupted content
