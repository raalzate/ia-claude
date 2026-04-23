# Phase 0 Research: Economic Optimization via Prefix Caching

## Decisions

### D-001 — Use the official `anthropic` Python SDK as the sole cache-observation surface

- **Decision**: Drive all requests through
  `anthropic.Anthropic().messages.create(...)` and read cache telemetry from
  the response object — specifically `response.usage.cache_creation_input_tokens`
  and `response.usage.cache_read_input_tokens`.
- **Rationale**: These two fields are the only first-class, typed signals the
  provider exposes for ephemeral-cache behaviour. Principle I forbids inferring
  control flow (here: "did the cache hit?") from anything softer; Principle II
  wants a typed field, and these are typed. Rolling a raw HTTP client would
  reimplement the same read without pedagogical gain.
- **Alternatives considered**:
  - *Infer cache hits from wall-clock latency.* Rejected: noisy, non-
    deterministic, and directly violates Principle I (probabilistic signal).
  - *Infer from billing totals post-hoc.* Rejected: too coarse, async, and
    unavailable inside the test loop.
  - *Third-party framework (LangChain / LlamaIndex).* Rejected: hides
    `cache_control` placement behind abstractions, defeating the kata.

### D-002 — `cache_control: {"type": "ephemeral"}` on static content blocks only

- **Decision**: The composer attaches `cache_control: {"type": "ephemeral"}`
  to each content block in the static system block and the static context
  block. Dynamic-suffix blocks carry **no** `cache_control` field.
- **Rationale**: The provider caches the *longest common prefix* of
  cache-marked segments. Marking only the static regions makes the intent
  explicit and the cache boundary observable in telemetry. Marking the suffix
  would invalidate the cache on every call (suffix is by definition variable)
  and produce false negatives in `cache_read_input_tokens`.
- **Alternatives considered**:
  - *Mark the whole prompt.* Rejected: guarantees a miss every call because
    the dynamic region changes.
  - *Mark nothing and rely on implicit caching.* Rejected: the kata's whole
    point is that prefix caching is an *explicit* economic lever.

### D-003 — Minimum-cacheable-size awareness with an explicit warning

- **Decision**: The composer measures the declared static region's token count
  (approximated via a conservative character-to-token heuristic tuned for the
  active model) and, when the region falls below the provider's stated
  minimum cacheable size, it omits `cache_control` and emits a
  `PrefixMutationDiagnostic` record of kind `under_min_size`. The test suite
  asserts the warning is emitted rather than silently falling back.
- **Rationale**: FR-007 demands an explicit signal when the optimization does
  not apply; silent fallback would look like a successful cache miss. Edge
  case "prompt smaller than minimum cacheable size" in the spec is operational-
  ized here.
- **Alternatives considered**:
  - *Raise hard.* Rejected: legitimate small prompts should still run; the
    kata only requires *observability*, not refusal.
  - *Pad the static region.* Rejected: fabricating tokens to game caching
    would teach the wrong lesson and inflate cost.

### D-004 — Two-region composer with composition-time interleaving rejection

- **Decision**: `PromptComposer` accepts exactly three slots —
  `static_system_block`, `static_context_block`, `dynamic_suffix_block` —
  and emits them in that fixed order. Any attempt to register a dynamic
  source inside a static slot raises `InterleavingRejected` at
  `build()` time, before the request is sent.
- **Rationale**: FR-001 and FR-003 require strict prefix/suffix partitioning
  with no interleaving. Catching this at composition time (rather than
  post-hoc in metrics) keeps the failure loud and local. Principle I
  discipline: reject on typed structural invariants, not on runtime inspection
  of generated output.
- **Alternatives considered**:
  - *Free-form list of blocks with a post-build linter.* Rejected: encourages
    "nearly right" prompts that only fail in CI, not locally.
  - *Single string concatenation.* Rejected: loses the structural boundary
    that `cache_control` relies on.

### D-005 — AST/regex lint over composer source

- **Decision**: A test at
  `tests/katas/010_prefix_caching/lint/test_no_dynamic_in_static.py` parses
  `katas/010_prefix_caching/composer.py` (and `blocks.py`) with the `ast`
  module, walks the static-block construction paths, and fails if it finds
  any reference to a non-allowlisted dynamic source: `datetime.*`, `time.*`,
  `uuid.*`, `os.environ*`, `getpass.*`, `socket.gethostname`, or any
  identifier from an explicit denylist (`timestamp`, `user_id`, `session_id`,
  `request_id`). Allowlist covers module-level constants and file reads
  declared at import time.
- **Rationale**: FR-005 and SC-003 require an automated CI gate for prefix
  integrity. This operationalizes the anti-pattern defense at the source
  level, not just at runtime — the same failure mode (developer interpolates
  a timestamp into the "static" system prompt) is caught before the code ever
  reaches the live API. Mirrors the Kata 001 "no prose matching" lint pattern.
- **Alternatives considered**:
  - *Runtime-only detection via cache_read telemetry.* Rejected: catches the
    bug only after it ships, too late for SC-004 (CI gate).
  - *Pure regex scan.* Rejected: fragile against string escaping and
    comments. AST gives structural confidence.

### D-006 — Measurement harness with declared-threshold assertion

- **Decision**: `harness.py` runs N ≥ 3 sequential requests sharing a byte-
  identical static prefix with varied suffixes, extracts `CacheMetric` from
  each response, and asserts that the cache-hit rate on runs 2..N meets the
  declared threshold (kata target: ≥ 0.9 after one warmup). In offline mode
  (default) the same assertions run against recorded `usage` blocks in
  `fixtures/`.
- **Rationale**: SC-001 and SC-002 require measurable reduction. A harness
  that computes the metric from typed fields — and runs identically offline
  and live — keeps the test deterministic (V) and reproducible on CI without
  API quota.
- **Alternatives considered**:
  - *Single live call.* Rejected: one call cannot demonstrate *reuse*.
  - *Compare two full billing cycles.* Rejected: out of scope and slow.

### D-007 — Mutation-injection test for the anti-pattern

- **Decision**: `test_mutation_breaks_cache.py` reuses the harness but
  deliberately prepends a per-iteration timestamp ahead of the static region
  on every call. It asserts that the cache-hit rate collapses to
  approximately zero and that `cache_read_input_tokens` is zero on runs 2..N.
- **Rationale**: User Story 2 / SC-002 delta / SC-004 demand that the anti-
  pattern fail *closed* and observably. Without this test the positive result
  is unfalsifiable.
- **Alternatives considered**:
  - *Narrative-only in README.* Rejected: Principle V / Kata Completion
    Standard #4 require a test that fails when the anti-pattern is
    reintroduced.

### D-008 — Declared-change marker to distinguish intentional mutation

- **Decision**: `PromptComposer.declare_prefix_change(reason: str)` stamps a
  `prefix_revision_id` onto the next emitted composition and the resulting
  `CacheMetric`. The metric schema carries an `intentional_prefix_change`
  boolean. Lint treats declared mutations as allowed.
- **Rationale**: FR-006 requires telemetry and lint to distinguish intentional
  prefix updates (a new tool is added, a system instruction legitimately
  changes) from accidental ones. Without this marker every legitimate change
  would trip the gate.
- **Alternatives considered**:
  - *Accept all prefix changes silently.* Rejected: defeats SC-004.
  - *Require a separate manifest file.* Rejected: extra ceremony outside the
    composer; the marker lives with the code that causes the change.

### D-009 — Recorded `usage` fixtures for offline tests

- **Decision**: Ship JSON fixtures capturing real `response.usage` blocks
  (model, input_tokens, output_tokens, cache_creation_input_tokens,
  cache_read_input_tokens) for the warm-cache path, cold-start path,
  mutation-break path, under-min-size path, and suffix-only-variation path.
  A `RecordedClient` returns them keyed by scenario id.
- **Rationale**: Determinism (V) and CI without API quota. Tests assert on
  `CacheMetric` shape and values derived from `usage`, which is exactly the
  contract under test.
- **Alternatives considered**:
  - *Synthesize `usage` values by hand.* Rejected: drift risk versus real
    SDK shape; the recording captures the ground truth.

### D-010 — `CacheMetric` JSONL log at `runs/<session-id>/metrics.jsonl`

- **Decision**: Each live run appends one `CacheMetric` record per request.
  Fields: `run_id`, `iteration`, `model`, `declared_target_hit_rate`,
  `cache_creation_input_tokens`, `cache_read_input_tokens`,
  `uncached_input_tokens`, `output_tokens`, derived `hit_rate`,
  `prefix_revision_id`, `intentional_prefix_change`, `under_min_size_warning`.
- **Rationale**: Principle VII (Provenance & Self-Audit). The economic claim
  ("input cost reduced to ~10% of baseline") is only credible if the raw
  metric record survives the run.

### D-011 — Tessl tile discovery

- **Decision**: No runtime library on the Tessl registry specifically wraps
  Anthropic's ephemeral cache_control / usage surface at a higher level of
  abstraction than the vendor SDK itself. The kata therefore depends on
  `anthropic`, `pydantic` v2, and `pytest` / `pytest-bdd` directly, matching
  the shared workshop baseline. No new Tessl tile is installed for Kata 10.
  If one appears in a later snapshot, the dependency block in `plan.md` is
  the one place to reconsider.
- **Rationale**: Principle-aligned minimalism; avoids introducing a wrapper
  that hides the very SDK fields (`cache_control`, `usage.cache_read_input_
  tokens`) the kata is meant to exercise.

## Open Questions

_None blocking Phase 1._ Provider-declared minimum cacheable size and exact
ephemeral TTL are read at runtime from the SDK / provider docs; the composer
treats both as configurable with defensive defaults.
