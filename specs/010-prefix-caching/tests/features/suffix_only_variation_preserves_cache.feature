# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-003
Feature: Dynamic Suffix Changes Preserve Prefix Cache
  Arbitrary edits to the dynamic suffix must not invalidate the static prefix cache; the suffix is the only safe locus of variability.

  Background:
    Given a prompt composition whose static prefix is byte-identical across runs
    And a dynamic suffix region delimited by a reminder tag
    And cache_control of type "ephemeral" is attached only to static-region content blocks

  @TS-012 @FR-003 @SC-001 @P3 @acceptance
  Scenario Outline: Arbitrary suffix edits preserve prefix cache hits across runs 2..N
    When the practitioner issues 3 sequential requests whose dynamic suffixes differ by <variation>
    Then iterations 2 and 3 each record cache_read_input_tokens covering the full static prefix region
    And the static-region source_digest is identical across all three iterations

    Examples:
      | variation              |
      | user question wording  |
      | appended timestamp tag |
      | session id value       |
      | reordered suffix lines |

  @TS-013 @FR-003 @SC-001 @P3 @acceptance
  Scenario: Suffix that grows in length between runs still yields prefix cache reads
    Given a sequence of requests where the dynamic suffix doubles in length between consecutive runs
    When the composer builds and issues the sequence within the cache TTL window
    Then the prefix cache still reports cache_read_input_tokens covering the full static prefix region on runs 2..N
    And no cache_control marker is attached to any dynamic-suffix content block

  @TS-014 @FR-003 @SC-003 @P3 @validation
  Scenario: Composer refuses to attach cache_control to a dynamic-suffix block
    Given a caller that attempts to set cache_control on a DynamicSuffixRegion content block
    When the composer builds the composition
    Then the composer raises a composition-time error
    And no request is emitted

  @TS-015 @FR-001 @FR-003 @P3 @validation
  Scenario: Composer rejects interleaved static and dynamic segments at build time
    Given a composition draft where a dynamic value appears between two static content blocks
    When the composer builds the composition
    Then the composer raises an InterleavingRejected error
    And no request is emitted

  @TS-016 @FR-001 @P3 @contract
  Scenario: PromptComposition records conform to the declared JSON schema
    Given a PromptComposition produced by the composer
    When the composition is validated against contracts/prompt-composition.schema.json
    Then the composition passes schema validation
    And static blocks precede the dynamic block in the emitted message list
