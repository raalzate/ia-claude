# Phase 1 Data Model: Economic Optimization via Prefix Caching

All entities are pydantic v2 models. Required fields are actually required;
optional fields use nullable unions rather than default empty strings
(Principle II).

## PromptComposition

The full assembled request. Two contiguous regions, no interleaving.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `composition_id` | `str` (UUIDv4) | yes | Identifies the composition for metric correlation. |
| `model` | `str` | yes | Anthropic model id, e.g. `claude-sonnet-4-5`. |
| `static_system_block` | `StaticPrefixRegion` | yes | System instructions + CLAUDE.md + tool definitions. |
| `static_context_block` | `StaticPrefixRegion \| None` | no | Heavy repo files; `None` when not needed. |
| `dynamic_suffix_block` | `DynamicSuffixRegion` | yes | User turn, timestamps, session state. |
| `prefix_revision_id` | `str \| None` | no | Stamped when `declare_prefix_change()` is called. |
| `intentional_prefix_change` | `bool` | yes | Defaults `False`; `True` when a prefix revision is declared. |
| `under_min_size_warning` | `bool` | yes | `True` when the static region falls below the cacheable threshold. |

**Invariants**:
- Static blocks always precede the dynamic block in the emitted message list.
- Any dynamic value found inside a static block raises `InterleavingRejected`
  at `PromptComposer.build()` time.
- `cache_control: {"type": "ephemeral"}` is set on static-block content
  **iff** `under_min_size_warning is False`.

**Serves**: FR-001, FR-003, FR-006, FR-007, edge case "interleaving".

## StaticPrefixRegion

A cache-markable region of the prompt.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `kind` | `Literal["system", "context"]` | yes | `system` for instructions + tool defs; `context` for repo files. |
| `content_blocks` | `list[ContentBlock]` | yes | Non-empty. Each block's text is byte-stable across calls in the cache window. |
| `cache_control` | `Literal["ephemeral"] \| None` | yes | `"ephemeral"` when above min size; `None` otherwise. |
| `declared_size_tokens` | `int` | yes | Conservative token estimate at composition time. |
| `source_digest` | `str` (sha256 hex) | yes | Digest of concatenated block text; used by the mutation detector. |

**Invariants**:
- `source_digest` changes iff the region's text changes. The metric pipeline
  compares digests across runs to attribute misses to prefix mutation.

**Serves**: FR-001, FR-002, FR-006, SC-003, SC-004.

## DynamicSuffixRegion

The variable portion of the prompt; never cache-marked.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `content_blocks` | `list[ContentBlock]` | yes | Non-empty. May include the current user turn, a timestamp reminder tag, session state. |
| `suffix_tag` | `str` | yes | Conventional reminder tag (e.g. `<dynamic>`) that visually and structurally marks the boundary. |
| `cache_control` | `Literal[None]` | yes | Must always be `None` — attempting to set it raises at composition time. |

**Invariants**:
- `cache_control` is structurally forbidden on this region (FR-003, SC-003).
- Any per-request value (timestamp, uuid, user input) MUST live here.

**Serves**: FR-003, SC-003.

## CacheMetric

Per-run record of cache behaviour. Extracted from `response.usage`.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `run_id` | `str` (UUIDv4) | yes | Groups an N-call measurement. |
| `composition_id` | `str` | yes | Links back to the `PromptComposition`. |
| `iteration` | `int` | yes | 1-indexed call number within the run. |
| `model` | `str` | yes | Model id echoed from the request. |
| `input_tokens` | `int` | yes | From `response.usage.input_tokens`. |
| `output_tokens` | `int` | yes | From `response.usage.output_tokens`. |
| `cache_creation_input_tokens` | `int` | yes | From `response.usage.cache_creation_input_tokens`. |
| `cache_read_input_tokens` | `int` | yes | From `response.usage.cache_read_input_tokens`. |
| `uncached_input_tokens` | `int` | yes | Derived: `input_tokens - cache_read_input_tokens`. |
| `hit_rate` | `float` | yes | Derived: `cache_read_input_tokens / (cache_read_input_tokens + uncached_input_tokens)` or `0.0` when denominator is zero. |
| `declared_target_hit_rate` | `float` | yes | Kata-declared threshold, e.g. `0.9`. |
| `prefix_revision_id` | `str \| None` | no | Echoed from the composition. |
| `intentional_prefix_change` | `bool` | yes | Echoed from the composition. |
| `under_min_size_warning` | `bool` | yes | Echoed from the composition. |

**Invariants**:
- `hit_rate` is recomputed, never trusted from external input.
- `iteration == 1` MUST have `cache_read_input_tokens == 0` (cold start) unless
  a prior run within the TTL warmed the cache; the harness tags this case
  separately.

**Serves**: FR-004, FR-007, SC-001, SC-002, Principle VII.

## PrefixMutationDiagnostic

Emitted by the lint step AND by the runtime mutation detector.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `kind` | `Literal["lint_violation", "runtime_mutation", "under_min_size"]` | yes | Distinguishes the three detection paths. |
| `composition_id` | `str \| None` | no | Present for runtime detections. |
| `file_path` | `str \| None` | no | Present for lint violations. |
| `line` | `int \| None` | no | Present for lint violations. |
| `offending_symbol` | `str \| None` | no | e.g. `datetime.datetime.now`, `os.environ['USER']`. |
| `previous_source_digest` | `str \| None` | no | For `runtime_mutation`. |
| `current_source_digest` | `str \| None` | no | For `runtime_mutation`. |
| `declared_as_intentional` | `bool` | yes | `True` when the composer's `declare_prefix_change()` was called for this revision. |
| `message` | `str` | yes | Human-readable reason. |

**Invariants**:
- Exactly one of (`file_path` + `line`) OR (`composition_id`) is populated,
  matching `kind`.
- `declared_as_intentional == True` MUST NOT appear with
  `kind == "lint_violation"` — intentional changes pass the lint by definition.

**Serves**: FR-005, FR-006, SC-003, SC-004.

## ContentBlock (shared primitive)

Thin wrapper over the SDK's text block to preserve block boundaries (needed
for per-block `cache_control`).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `type` | `Literal["text"]` | yes | Other block types are out of scope for this kata. |
| `text` | `str` | yes | Non-empty. |
| `cache_control` | `dict \| None` | no | `{"type": "ephemeral"}` or absent. Set by the composer, never by callers. |
