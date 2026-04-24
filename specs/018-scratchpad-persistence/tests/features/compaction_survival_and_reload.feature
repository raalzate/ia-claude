# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Compaction Survival and Non-Rediscovery on Reload
  After /compact or a new session the agent must read the scratchpad before any new query and must never rediscover facts it already recorded.

  Background:
    Given a declared scratchpad path under the session run directory
    And a ContextAnchor is seeded into each new session from the decisions and open_questions sections
    And a RecordedClient stands in for the live model unless LIVE_API=1 is set

  @TS-007 @FR-003 @SC-003 @US-002 @P2 @acceptance
  Scenario: Agent reads existing scratchpad before accepting the first user query of a new session
    Given a scratchpad with at least 1 recorded finding exists at the declared path
    When a new session starts
    Then the agent reads the scratchpad before accepting the first user query
    And the scratchpad contents are loaded as authoritative prior context

  @TS-008 @FR-009 @SC-001 @US-002 @P2 @acceptance
  Scenario: After /compact the agent re-reads the scratchpad before the next user query
    Given an active session reaches the 55% context-fill threshold
    When /compact is applied and the session resumes
    Then the agent re-reads the scratchpad before accepting the next user query
    And a ContextAnchor is recorded to anchor.json for audit

  @TS-009 @FR-009 @SC-001 @US-002 @P2 @acceptance
  Scenario: Post-compaction query about a recorded finding is answered with zero rediscovery tool calls
    Given a scratchpad records at least 5 tracked facts
    And a /compact reset has occurred
    When the practitioner asks a question whose answer is covered by a recorded finding
    Then the agent cites the scratchpad entry in its answer
    And zero rediscovery tool calls are issued for that fact
    And the rediscovery rate across the tracked facts is 0

  @TS-010 @FR-004 @US-002 @P2 @acceptance
  Scenario: New finding contradicting a recorded finding surfaces the conflict instead of overwriting
    Given the scratchpad already records a finding "module X is the router"
    When the agent records a new finding "module Y is the router" for the same target
    Then both entries are preserved in the "conflicts" section with cross-referenced ids
    And neither entry is silently overwritten
    And the human reader is surfaced the conflict for escalation

  @TS-011 @FR-007 @SC-003 @US-002 @P2 @acceptance
  Scenario: Missing scratchpad at session start results in a clean cold start
    Given no scratchpad file exists at the declared path
    When a new session starts
    Then the agent proceeds as a cold start with no prior context
    And no error is raised for the missing file
    And the scratchpad is created on the next write rather than at startup
