# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-001
Feature: Sequential Requests Hit the Prefix Cache
  Consecutive requests sharing a byte-identical static prefix must demonstrate observable KV cache reuse and a dramatic drop in billable input tokens.

  Background:
    Given a prompt composition whose static prefix exceeds the minimum cacheable size threshold
    And the static prefix carries cache_control of type "ephemeral" on its content blocks
    And the dynamic suffix region carries no cache_control marker

  @TS-001 @FR-001 @FR-004 @SC-001 @P1 @acceptance
  Scenario: Second back-to-back request reports cache hits and cost collapse
    When the practitioner issues the same composition twice back-to-back with different suffix content
    Then the second response reports a non-zero cache_read_input_tokens count on the static prefix
    And the billable non-cached input cost on the second request drops to at most 15 percent of the first-run baseline

  @TS-002 @FR-001 @FR-004 @SC-001 @SC-002 @P1 @acceptance
  Scenario Outline: Runs 2..N within the TTL window each hit the full static prefix
    When the practitioner issues <n> sequential requests sharing the static prefix within the cache TTL window
    Then iteration 1 records cache_creation_input_tokens greater than zero and cache_read_input_tokens equal to zero
    And iterations 2..<n> each record cache_read_input_tokens covering the full static prefix region
    And the derived hit_rate across iterations 2..<n> is at least 0.90

    Examples:
      | n |
      | 3 |
      | 5 |

  @TS-003 @FR-004 @SC-002 @P1 @acceptance
  Scenario: Billable input tokens drop by at least 85 percent after warmup
    Given a measurement harness run with a fixed static prefix and varied dynamic suffixes
    When the harness completes N sequential calls within the cache TTL window
    Then the mean billable input token count for iterations 2..N is at most 15 percent of the iteration-1 baseline

  @TS-004 @FR-004 @P1 @contract
  Scenario: CacheMetric records conform to the declared JSON schema
    Given a CacheMetric JSONL log produced by a harness run
    When each record is validated against contracts/cache-metric-record.schema.json
    Then every record passes schema validation
    And every record carries input_tokens, cache_creation_input_tokens, cache_read_input_tokens, uncached_input_tokens, and hit_rate fields

  @TS-005 @FR-007 @P1 @validation
  Scenario: Static region below the minimum cacheable size emits an explicit warning
    Given a prompt composition whose static prefix falls below the minimum cacheable size threshold
    When the composer builds the request
    Then the composition reports under_min_size_warning equal to true
    And no cache_control marker is attached to any content block
