# Kata 8 — Quickstart

## What you'll build

A canonical `.claude/CLAUDE.md` + `standards/` layout PLUS a Python
`MemoryResolver` library that (a) resolves `@path` references deterministically,
(b) distinguishes team vs. personal scope, (c) detects cycles, (d) fails loud
on missing targets, (e) enforces an aggregated size cap for team memory.

## Prerequisites

- Python 3.11+
- `pip`
- `ANTHROPIC_API_KEY` only for the equivalence probe run (optional)

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/008_claude_md_memory -v
```

Scenarios covered:
- valid-hierarchy — resolves in order, no diagnostics.
- missing-`@path` → `ResolutionDiagnostic code=missing_path_target` (fail loud).
- circular-reference → diagnostic with full chain.
- oversized-team-tree → `team_size_exceeded`.
- conflicting personal vs. team → personal entry marked `scope=personal` and NOT effective for project tasks.

## Run the fresh-clone equivalence probe (optional, LIVE_API)

```bash
LIVE_API=1 python -m katas.008_claude_md_memory.probe \
  --repo-path . --prompts tests/katas/008_claude_md_memory/fixtures/probe_prompts.json
```

Sends a calibrated prompt to the Claude API with resolved memory attached.
Runs twice against the same repo tree and asserts byte-identical responses on
the declared prompt set (SC-001).

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Fresh clone behaves identically | US1, SC-001 | `valid_hierarchy/` |
| Personal rule doesn't override team | US2, SC-002 | `conflicting_personal/` |
| `@path` target edit visible without CLAUDE.md edit | US3 | `live_reference_edit/` |
| Missing `@path` fails loud | Edge #1, FR-004 | `missing_target/` |
| Circular `@path` detected | Edge #2 | `circular_chain/` |
| Oversized tree rejected | Edge #4, SC-003 | `oversized_tree/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending testify + tasks.
- [x] Anti-pattern (personal-scope team rules, monolithic memory) defended by
      fixtures + size-cap lint.
- [ ] `README.md` — at `/iikit-07-implement`.
- [ ] *Why*-comments on resolver recursion and cycle detection.

## Reflection prompt

- Which `@path` in this repo's own `.tessl/RULES.md` chain would most surprise
  a new contributor, and does the resolver surface that clearly?
- How would the size cap interact with a truly large team standard set — split
  or compress?
