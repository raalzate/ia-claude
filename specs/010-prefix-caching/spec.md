# Feature Specification: Economic Optimization via Prefix Caching

**Feature Branch**: `010-prefix-caching`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 10 — Reduce token cost to approximately 10% of baseline by structuring model context to maximize KV prefix-cache reuse. Place static content (system instructions, CLAUDE.md, tool definitions, heavy repo context) at the start of the prompt; confine dynamic/variable content (user input, timestamps, ephemeral state) to the end using XML reminder tags or equivalent."

## User Stories *(mandatory)*

### User Story 1 - Sequential Requests Hit the Cache (Priority: P1)

A practitioner sends N consecutive requests that share a large static preamble (system instructions, repository context, tool definitions) and only vary in the dynamic suffix. After the first request warms the cache, subsequent requests report cache hits on the shared prefix and a dramatic drop in billable input tokens.

**Why this priority**: This is the core economic outcome of the kata. Without demonstrable cache reuse across sequential calls, the entire optimization is unobservable and the cost target cannot be met.

**Independent Test**: Run the kata runner with a fixed static prefix and a set of varied dynamic suffixes; assert that cache-hit rate on runs 2..N is ≥ 0.90 and that per-request billable input tokens drop by ≥ 85% relative to run 1.

**Acceptance Scenarios**:

1. **Given** a prompt composed of a static prefix above the minimum cacheable size and a small dynamic suffix, **When** the practitioner issues the same composition twice back-to-back with different suffix content, **Then** the second response reports a non-zero cache-read token count on the static prefix and the billable (non-cached) input cost drops to ≤ 15% of the baseline.
2. **Given** a sequence of N requests sharing the same static prefix, **When** they run within the cache TTL window, **Then** runs 2..N each report cache hits covering the full static prefix region.

---

### User Story 2 - Anti-Pattern Defense: Prefix Mutation Breaks Caching (Priority: P2)

A practitioner deliberately injects a volatile value (e.g., a timestamp or request ID) at the very top of the prompt, ahead of the static preamble. The run demonstrates that the cache-hit rate collapses, proving that the strict-prefix-match behavior of the API is sensitive to any early mutation.

**Why this priority**: The kata's educational value depends on the practitioner internalizing why prefix mutation is catastrophic. This story makes the failure mode concrete and measurable rather than theoretical.

**Independent Test**: Re-run the P1 sequence after prepending a per-request timestamp to the prompt; assert that cache-hit metrics fall to approximately zero and that input cost returns to the uncached baseline.

**Acceptance Scenarios**:

1. **Given** the same static prefix and dynamic suffix as User Story 1, **When** a per-request timestamp is prepended ahead of the static region, **Then** every run reports zero cache hits on the static prefix and input cost equals the uncached baseline.
2. **Given** a PR that reorders content so volatile values appear before the static region, **When** CI runs the prefix-integrity lint, **Then** the build fails and the offending line is reported.

---

### User Story 3 - Dynamic Suffix Changes Preserve Prefix Cache (Priority: P3)

A practitioner modifies only the dynamic suffix (user question, session state, timestamp reminder) between consecutive runs while keeping the static prefix byte-identical. Cache hits on the prefix are preserved across all runs regardless of suffix content.

**Why this priority**: This confirms the positive invariant complementary to Story 2: the suffix is the only safe place for variability, and arbitrary suffix edits do not invalidate the prefix.

**Independent Test**: Run a sequence where each request has a distinct suffix but a byte-identical static region; assert prefix cache hits on runs 2..N regardless of suffix content, length, or structure.

**Acceptance Scenarios**:

1. **Given** a byte-identical static prefix across runs, **When** the dynamic suffix changes arbitrarily between runs, **Then** the prefix cache still reports hits on runs 2..N.
2. **Given** a dynamic suffix that grows in length between runs, **When** the prefix remains unchanged, **Then** cache reads still cover the full static prefix region.

---

### Edge Cases

- Prompt is smaller than the minimum cacheable size declared by the API; no cache entry is created and the cost optimization does not apply — the run MUST report this condition explicitly rather than silently falling back.
- Cache entry expires between requests (TTL elapsed); the next request behaves like a cold start and subsequent requests within the new window resume caching.
- Tool definitions or system instructions change legitimately (e.g., a new tool is added); the prefix is intentionally mutated and the next run is a cold start — this MUST be distinguishable in metrics from an accidental mutation.
- Dynamic content unexpectedly includes non-deterministic values embedded inside what was declared static (e.g., a UUID interpolated into a system instruction); the prefix lint MUST detect the volatile token.
- The composed prompt mixes static and dynamic segments (interleaving) rather than keeping them contiguous; the composition step MUST reject or flag this arrangement.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST place all static content (system instructions, repository context such as CLAUDE.md, tool definitions) strictly before any dynamic content in the composed prompt.
- **FR-002**: System MUST treat tool definitions and system instructions as part of the static prefix region and never interpolate per-request values into them.
- **FR-003**: System MUST confine all volatile or per-request values (user input, timestamps, session identifiers, ephemeral state) to a declared dynamic-suffix region delimited by reminder tags or an equivalent convention.
- **FR-004**: System MUST report a measurable cache-hit rate and a cached-vs-uncached input token breakdown for every run.
- **FR-005**: System MUST flag any prefix mutation during code review via an automated lint step, and the CI gate MUST fail on detection.
- **FR-006**: System MUST distinguish intentional prefix changes (declared in the PR) from accidental prefix mutation in its metrics and lint output.
- **FR-007**: System MUST declare and document the minimum cacheable prefix size threshold and MUST emit a warning when a run falls below it.

### Key Entities *(include if feature involves data)*

- **Prompt Composition**: The full assembled prompt sent to the model. Composed of exactly two contiguous regions — a static prefix region followed by a dynamic suffix region — with no interleaving permitted.
- **Static Prefix Region**: The stable, reusable portion of the prompt. Contains system instructions, repository context (e.g., CLAUDE.md), and tool definitions. Byte-identical across sequential requests within a session's cache window.
- **Dynamic Suffix Region**: The variable portion of the prompt. Contains user input, timestamps, session state, and any other per-request values. Demarcated by reminder tags or an equivalent structural marker.
- **Cache Metric**: The per-run record of cache behavior. Includes cache-read token count, cache-write token count, uncached input token count, and derived cache-hit rate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cache-hit rate is ≥ 0.90 on runs 2..N within the cache TTL window across the test corpus.
- **SC-002**: Billable input token cost per request after the first drops to ≤ 15% of the uncached baseline.
- **SC-003**: Zero volatile tokens are detected in the static prefix region by the lint step across the entire repository.
- **SC-004**: Pull requests that mutate the static prefix (without an explicit declared change) fail CI on the prefix-integrity check.

## Clarifications

- **FR-007 minimum cacheable prefix size**: The declared threshold is **1024 tokens** (Anthropic documented minimum for ephemeral cache). A static prefix below this size MUST NOT carry `cache_control`, and the composer MUST emit an explicit `under_min_size_warning` rather than silently falling back.
- **Cache TTL window**: The ephemeral cache TTL is **5 minutes**. Runs 2..N asserted against SC-001 / SC-002 thresholds are required to execute within this window of the cold-start warmup run; beyond that, the next request behaves like a cold start per the edge-case rule.
- **Cache breakpoint budget**: A single request MUST carry **≤ 4 cache breakpoints** (`cache_control` markers). This is the API-imposed budget; the composer's block builders are responsible for keeping the count at or under four across a composed `PromptComposition`.
