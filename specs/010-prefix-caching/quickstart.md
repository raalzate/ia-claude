# Kata 10 — Quickstart

## What you'll build

A `PromptComposer` with three declared regions (static-system, static-context,
dynamic-suffix) that marks only the static regions with `cache_control`. An
AST lint refuses volatile tokens in the static regions. A measurement harness
reads `response.usage.cache_read_input_tokens` to prove the cache is hitting.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/010_prefix_caching -v
```

Includes:
- AST lint: scans `katas/010_prefix_caching/composer.py`, fails the build if
  `datetime.now`, `os.environ`, `uuid.uuid4`, or any module-level timestamp is
  reached from a static region.
- Fixture replay: recorded `usage` blocks assert cache-hit rate progression
  across sequential requests.

## Run the live cache probe

```bash
LIVE_API=1 python -m katas.010_prefix_caching.probe --n 5
```

Sends 5 sequential requests with identical static prefix. Prints:

```
req 1: input=3450  cache_create=3450  cache_read=0      hit=0.00
req 2: input=140   cache_create=0     cache_read=3450   hit=0.96
req 3: input=140   cache_create=0     cache_read=3450   hit=0.96
...
```

Asserts cache-hit rate ≥ declared threshold after warmup (see `research.md`).

## Run the prefix-mutation anti-pattern demo

```bash
LIVE_API=1 python -m katas.010_prefix_caching.probe --mutate-prefix
```

Inserts a `datetime.now()` at the top of the static prefix. Asserts cache-hit
rate drops near zero — the demonstrable SC-002 delta.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Warm cache reduces cost | US1, SC-001 | recorded usage sequence |
| Mutating prefix kills cache | US2, SC-002 | `mutated_prefix_run.json` |
| Modifying suffix only preserves cache | US3 | `suffix_only_diff.json` |
| Small-prompt minimum guarded | Edge #1 | `below_min_size.json` |
| Lint fails on volatile in static | FR-005, SC-003 | composer test |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Anti-pattern (prefix mutation) defended by AST lint + live demo.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- Why did cache-hit-rate recover after the mutation test? What does that tell
  you about cache TTL vs. prefix stability?
