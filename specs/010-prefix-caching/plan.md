# Implementation Plan: Economic Optimization via Prefix Caching

**Branch**: `010-prefix-caching` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/010-prefix-caching/spec.md`

## Summary

Kata 10 delivers a `PromptComposer` that assembles Messages API requests in two
strictly contiguous regions: a **static prefix** (system instructions, CLAUDE.md,
tool definitions, heavy repo context) carrying `cache_control: {"type":
"ephemeral"}` on its content blocks, and a **dynamic suffix** (user turn,
timestamps, session IDs) that carries no cache marker. The module surfaces
Anthropic's per-response `usage.cache_creation_input_tokens` /
`cache_read_input_tokens` as first-class metrics so the kata can *prove*
reuse rather than infer it from cost curves. An AST/regex lint gate and a
mutation-injection test operationalize the anti-pattern defense (FR-002,
FR-005, FR-006, SC-002 delta, SC-003, SC-004). The design satisfies
Constitution v1.3.0 Principles II (Schema-Enforced Boundaries, NN), III
(Context Economy — the central principle of this kata), and VIII (Mandatory
Documentation, NN).

## Technical Context

**Language/Version**: Python 3.11+.
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — **load-bearing**. The composer emits
  message blocks with `cache_control: {"type": "ephemeral"}`; metrics are
  pulled from `response.usage.cache_creation_input_tokens` and
  `response.usage.cache_read_input_tokens`. No other vendor field gives
  observable cache behaviour, so the kata cannot be taught without the SDK.
- `pydantic` v2 — schema enforcement for `PromptComposition`,
  `StaticPrefixRegion`, `DynamicSuffixRegion`, and `CacheMetric`
  (Principle II).
- `pytest` + `pytest-bdd` — BDD runner consuming the `.feature` file
  produced by `/iikit-04-testify` (Principle V / TDD).
**Storage**: Local filesystem only. Recorded fixtures under
`tests/katas/010_prefix_caching/fixtures/` hold `response.usage` snapshots for
offline runs. Live runs append per-call `CacheMetric` records to
`runs/<session-id>/metrics.jsonl` (gitignored).
**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit tests and the composer-source lint. Offline-first: fixture-backed test
runs are the default and MUST be green before any `LIVE_API=1` run.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). CI runs the offline suite only.
**Project Type**: Single project — one kata module at
`katas/010_prefix_caching/` with tests under `tests/katas/010_prefix_caching/`.
**Performance Goals**: Not latency-bound. Offline acceptance run completes in
under 5 seconds. Live `LIVE_API=1` measurement harness issues N ≥ 3 sequential
calls with a shared static prefix and reports cache-hit rate within the
provider's ephemeral-cache TTL window.
**Constraints**:
- Static blocks below the API's minimum cacheable size MUST NOT carry
  `cache_control`; the composer MUST emit a typed warning in that case
  (FR-007).
- The composer MUST refuse to emit a prompt where dynamic values appear
  before, inside, or interleaved with static blocks — rejection is at
  composition time, not at runtime inspection (FR-001, FR-003, edge case
  "interleaving").
- No `cache_control` on dynamic-suffix blocks (FR-003, SC-003).
- Lint MUST reject any non-allowlisted dynamic source (timestamps, UUIDs,
  `os.environ`, session IDs) referenced from within static-block construction
  (FR-002, FR-005).
**Scale/Scope**: One kata, ~350–500 LOC implementation + comparable test
code; one README; fixture corpus ≤ 8 recorded `usage` snapshots covering the
warm-cache happy path, the prefix-mutation anti-pattern, suffix-only variation,
and the under-minimum-size edge case.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Cache-hit assertions key off `response.usage.cache_read_input_tokens` (a typed SDK field), never off prose or cost curves. |
| II. Schema-Enforced Boundaries (NN) | `PromptComposition`, `StaticPrefixRegion`, `DynamicSuffixRegion`, `CacheMetric` are pydantic v2 models with required fields and nullable unions for "no cache entry"; invalid compositions raise at `model_validate` time. |
| III. Context Economy | Load-bearing. The entire kata is the enforcement mechanism for this principle: stable-prefix / dynamic-suffix ordering is the composer's invariant, and `cache_control` placement is the observable proof. |
| IV. Subagent Isolation | Not applicable — single-agent kata. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code; the measurement harness and mutation-injection test are generated from Gherkin and referenced by `tasks.md`. |
| VI. Human-in-the-Loop | The composer emits a typed `UnderMinimumCacheableSize` diagnostic rather than silently degrading (FR-007, edge case). |
| VII. Provenance & Self-Audit | Each live run appends a `CacheMetric` JSONL record with model, declared target, cache-read tokens, cache-creation tokens, uncached tokens, and derived hit rate — sufficient to reconstruct the economic claim. |
| VIII. Mandatory Documentation (NN) | `why` comments on every non-trivial composer branch (tied to FR-001/FR-002/FR-003); README covers objective, walkthrough, anti-pattern defense, run instructions, reflection (produced during `/iikit-07-implement`). |

**Result:** PASS. Proceed to Phase 1 design.

## Project Structure

### Documentation (this feature)

```text
specs/010-prefix-caching/
  plan.md              # this file
  research.md          # Phase 0 output (decisions D-001..N)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output (JSON schemas, $id kata-010)
    prompt-composition.schema.json
    cache-metric-record.schema.json
    prefix-mutation-diagnostic.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  010_prefix_caching/
    __init__.py
    composer.py          # PromptComposer with static_system_block, static_context_block, dynamic_suffix_block
    blocks.py            # block builders; attaches cache_control only to static regions; min-size awareness
    metrics.py           # CacheMetric extraction from response.usage + JSONL writer
    harness.py           # measurement harness: N sequential calls, offline-or-LIVE_API, hit-rate assertion
    mutation.py          # deliberate-mutation helper for the anti-pattern test
    client.py            # thin injectable Anthropic client wrapper (recorded-or-live)
    models.py            # pydantic models: PromptComposition, StaticPrefixRegion, DynamicSuffixRegion, CacheMetric
    runner.py            # CLI: `python -m katas.010_prefix_caching.runner`
    README.md            # kata narrative (written during /iikit-07)

tests/
  katas/
    010_prefix_caching/
      conftest.py        # fixture loader, LIVE_API gate, hit-rate tolerance helpers
      features/          # Gherkin produced by /iikit-04-testify
        prefix_caching.feature
      step_defs/
        test_prefix_caching_steps.py
      unit/
        test_composer_ordering.py       # FR-001, FR-003, interleaving rejection
        test_cache_control_placement.py # FR-002, FR-003, SC-003
        test_min_size_warning.py        # FR-007, edge case
        test_cache_metric_shape.py      # II + VII
      lint/
        test_no_dynamic_in_static.py    # AST/regex gate: FR-002, FR-005, SC-003
      harness/
        test_warm_cache_hit_rate.py     # SC-001, SC-002 (US1)
        test_mutation_breaks_cache.py   # SC-002 delta, SC-004 (US2)
        test_suffix_only_variation.py   # US3
      fixtures/
        warm_cache.json                # recorded usage blocks: runs 1..N, rising cache_read_input_tokens
        cold_start.json                # usage with cache_creation_input_tokens only
        mutation_break.json            # usage with zero cache_read after prefix mutation
        under_min_size.json            # usage with no cache entry; warning path
        suffix_only_variation.json     # usage showing prefix reuse across varied suffixes
```

**Structure Decision**: Single-project layout, matching the baseline established
by Kata 001. Each kata is a first-class package under `katas/NNN_<slug>/`; tests
mirror that structure under `tests/katas/NNN_<slug>/`. Live runs write to
`runs/<session-id>/metrics.jsonl` (gitignored). This keeps the 20 katas
independently buildable per FDD delivery cadence.

## Traceability: Tech → FR/SC

| Tech choice | Serves |
|-------------|--------|
| `anthropic` SDK + `cache_control: {"type": "ephemeral"}` on static blocks | FR-001, FR-002, FR-003, SC-001, SC-002 |
| `response.usage.cache_read_input_tokens` as the assertion source | FR-004, SC-001, SC-002 |
| Two-region `PromptComposer` with composition-time rejection of interleaving | FR-001, FR-003, edge case "interleaving" |
| AST/regex lint over composer source | FR-002, FR-005, SC-003, SC-004 |
| Mutation-injection test | FR-005, FR-006, SC-002 delta, SC-004 |
| Minimum-cacheable-size gate + warning | FR-007, edge case "below minimum" |
| Declared-change marker vs accidental mutation | FR-006 |
| `CacheMetric` pydantic model + JSONL log | II, IV reporting obligation, FR-004 |

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  Prompt Composer   │───────│   Mutation Lint    │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Messages API  │ │Cache Metric Log│ │Cache Fixture R…│
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `Prompt Composer` owns the core control flow
for this kata's objective; `Mutation Lint` is the primary collaborator/policy reference;
`Messages API`, `Cache Metric Log`, and `Cache Fixture Replay` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: retry / backoff on API errors,
multi-model comparison, streaming responses, cache-aware batching across
sessions — none are required by the spec or the constitution, and expanding
scope would dilute the kata's single pedagogical point (prefix-cache reuse).
