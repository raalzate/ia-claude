# DO NOT MODIFY SCENARIOS
# Derived from requirements. Fix code to pass tests; re-run /iikit-04-testify if requirements change.

@US-002
Feature: Prefix Mutation Breaks Caching (Anti-Pattern Defense)
  Any volatile value prepended to or embedded within the static prefix must collapse cache hits and be caught by automated lint before merge.

  Background:
    Given a baseline prompt composition that produces cache hits on iterations 2..N
    And a lint gate that inspects composer source for dynamic symbols in static regions
    And a runtime mutation detector that compares static-region source digests across iterations

  @TS-006 @FR-002 @FR-005 @SC-003 @P2 @acceptance
  Scenario: Per-request timestamp prepended ahead of static region zeroes out cache hits
    When a per-request timestamp is prepended ahead of the static prefix region
    Then every iteration reports cache_read_input_tokens equal to zero
    And the mean billable input token count equals the uncached baseline

  @TS-007 @FR-005 @SC-004 @P2 @validation
  Scenario: CI prefix-integrity lint fails on PR reordering volatile values before static region
    Given a pull request that reorders composer source so a volatile value appears before the static region
    When CI runs the prefix-integrity lint step
    Then the build fails
    And the lint output reports the offending file path and line
    And the offending symbol is named in the diagnostic

  @TS-008 @FR-002 @FR-005 @SC-003 @P2 @validation
  Scenario Outline: Lint rejects non-allowlisted dynamic sources referenced from static-block construction
    Given composer source that references <symbol> inside a static-block builder
    When the prefix-integrity lint runs over the source tree
    Then the lint emits a PrefixMutationDiagnostic of kind "lint_violation"
    And the diagnostic names <symbol> as the offending symbol
    And declared_as_intentional is false in the diagnostic

    Examples:
      | symbol                      |
      | datetime.datetime.now       |
      | uuid.uuid4                  |
      | os.environ                  |
      | time.time                   |

  @TS-009 @FR-006 @P2 @acceptance
  Scenario: Intentional prefix revision is distinguishable from accidental mutation
    Given the composer declares a prefix revision via declare_prefix_change with a revision id
    When the next run executes
    Then the first iteration records cache_creation_input_tokens greater than zero and cache_read_input_tokens equal to zero
    And the CacheMetric record echoes intentional_prefix_change equal to true
    And the prefix_revision_id field is populated on the metric record

  @TS-010 @FR-006 @SC-004 @P2 @validation
  Scenario: Accidental runtime prefix mutation emits a runtime_mutation diagnostic
    Given a run whose static-region source digest differs from the prior run within the TTL window
    And no declare_prefix_change call preceded the run
    When the runtime mutation detector compares digests
    Then a PrefixMutationDiagnostic of kind "runtime_mutation" is emitted
    And the diagnostic carries previous_source_digest and current_source_digest fields
    And declared_as_intentional is false in the diagnostic

  @TS-011 @FR-002 @FR-005 @P2 @contract
  Scenario: PrefixMutationDiagnostic records conform to the declared JSON schema
    Given a PrefixMutationDiagnostic record produced by lint or runtime detection
    When the record is validated against contracts/prefix-mutation-diagnostic.schema.json
    Then the record passes schema validation
    And the kind field is one of "lint_violation", "runtime_mutation", "under_min_size"
