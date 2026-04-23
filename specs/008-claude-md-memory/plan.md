# Implementation Plan: Hierarchical Memory Orchestration in CLAUDE.md

**Branch**: `008-claude-md-memory` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/008-claude-md-memory/spec.md`

## Summary

Kata 8 is **governance-as-code**, not a runtime library. The primary
deliverables are **configuration artifacts** committed to the repo:

1. A canonical project memory file (`.claude/CLAUDE.md`) that encodes universal
   team coding conventions for this workshop.
2. A `standards/` directory of modular manuals (`coding-style.md`, `testing.md`,
   `commit-message.md`) pulled into effective memory through `@path` references
   — the exact pattern already in use by this repo's own `CLAUDE.md` →
   `AGENTS.md` → `.tessl/RULES.md` chain.
3. A *small* Python library, `MemoryResolver`, that mechanically validates the
   chain: reads a `CLAUDE.md`, recursively resolves `@path` references, returns
   a deterministic `ResolvedMemory` pydantic model, and fails loud on cycles,
   missing targets, or oversize aggregated memory.

The library is intentionally **light-touch**: it exists to make governance
files *testable* (determinism SC-001, precedence SC-002, missing-target
diagnostic SC-004, size budget SC-003) — not to serve runtime agent memory.
The agent itself still consumes `CLAUDE.md` via the native `@path` mechanism;
the resolver is a lint / CI tool, not a replacement loader.

Delivered under Constitution v1.3.0 Principles III (Context Economy, via the
size budget) and VIII (Mandatory Documentation, via the modular-manuals
pattern and per-kata `README.md`).

## Technical Context

**Language/Version**: Python 3.11+ (matches kata 001 baseline).
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — used **only** by the fresh-clone
  behavior-equivalence test (SC-001): one scripted prompt sent to a Claude
  model, two independent clones of the repo asserted to produce byte-identical
  `ResolvedMemory` plus matching agent output category. Not required for
  resolver-level tests or day-to-day validator runs.
- `pydantic` v2 — declarative schema for `ResolvedMemory`, `MemoryEntry`,
  `PathReference`, `ResolutionDiagnostic` (Principle II).
- `pytest` + `pytest-bdd` — Gherkin scenarios from `/iikit-04-testify`,
  plain `pytest` for unit tests over the resolver and fixtures.
- Standard library only for filesystem + graph traversal (`pathlib`,
  `hashlib`, `collections`) — no YAML/TOML parser, no third-party graph
  library.

**Storage**: Files on disk. No database. The validator reads committed memory
files; the behavior-equivalence test writes a small JSON diagnostics report
under `runs/<session-id>/memory_diagnostics.json` (gitignored).

**Testing**: pytest + pytest-bdd. Five fixture trees live under
`tests/katas/008_claude_md_memory/fixtures/`:
- `valid/` — well-formed hierarchy with `@path` references into `standards/`.
- `missing_target/` — `@path` points to a file that does not exist (fail-loud).
- `circular/` — A references B, B references A (fail-loud with cycle report).
- `oversize/` — aggregated memory exceeds `TEAM_MEMORY_MAX_BYTES`.
- `personal_vs_team/` — a `~/.claude/CLAUDE.md` (redirected via env var) whose
  rule conflicts with a rule in `.claude/CLAUDE.md`.

**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.

**Project Type**: Single project. One kata module under
`katas/008_claude_md_memory/` with its own tests alongside. The canonical
template + standards ship as *config artifacts* inside that module and are
copied / symlinked into the repo root during the kata's implement phase.

**Performance Goals**: Not latency-bound. `MemoryResolver.resolve()` on the
valid fixture (≤20 KB aggregated) completes in <50 ms locally. Full test
suite (pytest-bdd + unit + lint) under 3 s.

**Constraints**:
- `TEAM_MEMORY_MAX_BYTES = 20 * 1024` — declared in the module; the lint test
  `test_team_memory_size_budget.py` fails the build if aggregated team memory
  from the canonical template exceeds this. (SC-003, FR-007, Principle III.)
- Determinism: two independent resolver runs on the same source tree MUST
  produce a byte-identical JSON serialization of `ResolvedMemory`. Enforced by
  `test_resolver_deterministic.py`. (SC-001, FR-005.)
- Fail-loud: missing `@path`, cycles, unreadable files MUST raise a typed
  exception carrying a `ResolutionDiagnostic`. Silent skip of a reference is
  a bug. (SC-004, FR-004.)
- Scope separation: the resolver MUST label every `MemoryEntry` with
  `scope ∈ {"team", "personal"}`. The `effective_for_project_task()` view
  MUST drop personal entries whose rule keys collide with a team rule.
  (SC-002, FR-003, FR-006.)

**Scale/Scope**: One kata, ~200–300 LOC resolver + comparable test code; one
README; five fixture trees; three JSON schemas; one canonical template
(`.claude/CLAUDE.md`) + three standards manuals.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | `ResolvedMemory` ordering is derived from the deterministic DFS of `@path` declarations in the source file, not from any model output. The behavior-equivalence test asserts byte-identical JSON, not prose similarity. |
| II. Schema-Enforced Boundaries (NN) | `ResolvedMemory`, `MemoryEntry`, `PathReference`, `ResolutionDiagnostic` are pydantic v2 models with JSON Schema mirrors under `contracts/`. Invalid payloads raise `ValidationError`. |
| III. Context Economy | `TEAM_MEMORY_MAX_BYTES` budget + modular `@path` split enforces the "don't inline everything at the top of the window" rule. The budget is the machine-checkable face of Principle III for this kata. |
| IV. Subagent Isolation | Not applicable — no subagents in this kata. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code; tasks reference `.feature` test IDs; red→green→refactor enforced. |
| VI. Human-in-the-Loop | Missing-target / cycle diagnostics halt the tool with a labelled exception; the reviewer is the escalation target. No silent degradation path exists. |
| VII. Provenance & Self-Audit | Every `MemoryEntry` in `ResolvedMemory` carries `source_path` (absolute), `source_sha256`, and `declaration_order` so aggregated rules can always be traced back to the file they came from. Matches Principle VII. |
| VIII. Mandatory Documentation (NN) | The kata IS a documentation kata — its whole output is governance manuals. The per-kata `README.md` covers objective, walkthrough, the personal-pollutes-team anti-pattern, run instructions, and reflection. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/008-claude-md-memory/
  plan.md                     # this file
  research.md                 # Phase 0 output (D-001..D-007, Tessl note)
  data-model.md               # Phase 1 output (pydantic entity shapes)
  quickstart.md               # Phase 1 output (install, validator run, scenario map)
  contracts/                  # Phase 1 output (JSON schemas, $id kata-008)
    resolved-memory.schema.json
    memory-entry.schema.json
    path-reference.schema.json
    resolution-diagnostic.schema.json
  tasks.md                    # Phase 2 output (/iikit-05-tasks)
  checklists/
    requirements.md           # produced by /iikit-03-checklist (already present)
  README.md                   # Principle VIII deliverable (written at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  008_claude_md_memory/
    __init__.py
    resolver.py               # MemoryResolver: read, recurse @path, build ResolvedMemory
    models.py                 # pydantic v2: ResolvedMemory, MemoryEntry, PathReference,
                              #   ResolutionDiagnostic, scope enums
    budget.py                 # TEAM_MEMORY_MAX_BYTES + size accounting helpers
    scope.py                  # team-vs-personal precedence logic (SC-002, FR-006)
    cli.py                    # `python -m katas.008_claude_md_memory.cli validate <path>`
    templates/
      CLAUDE.md               # canonical project memory template (@path chain)
      standards/
        coding-style.md
        testing.md
        commit-message.md
    README.md                 # kata narrative (written during /iikit-07)

tests/
  katas/
    008_claude_md_memory/
      conftest.py             # fixture loaders, HOME redirect for personal memory
      features/               # Gherkin from /iikit-04-testify
        hierarchical_memory.feature
      step_defs/
        test_hierarchical_memory_steps.py
      unit/
        test_resolver_deterministic.py     # SC-001, FR-005
        test_personal_override_blocked.py  # SC-002, FR-003, FR-006
        test_missing_target_fails_loud.py  # SC-004, FR-004
        test_circular_reference.py         # FR-004 edge
        test_team_memory_size_budget.py    # SC-003, FR-007, Principle III
        test_resolved_memory_schema.py     # Principle II — JSON-Schema mirror check
      fixtures/
        valid/
          .claude/CLAUDE.md
          standards/coding-style.md
          standards/testing.md
        missing_target/
          .claude/CLAUDE.md           # references standards/ghost.md (does not exist)
        circular/
          .claude/CLAUDE.md           # @./a.md
          a.md                        # @./b.md
          b.md                        # @./a.md  (cycle)
        oversize/
          .claude/CLAUDE.md           # references a 25 KB manual
          standards/huge.md
        personal_vs_team/
          project/.claude/CLAUDE.md   # team rule: "use pnpm"
          home/.claude/CLAUDE.md      # personal rule: "use npm"
```

**Structure Decision**: Single-project layout matching kata 001. The
canonical `.claude/CLAUDE.md` + `standards/*.md` live inside the kata's
`templates/` directory so they are *source-controlled artifacts* owned by
this kata, then symlinked or copied to the repo root during
`/iikit-07-implement`. This preserves clean per-kata deletion and avoids
coupling the kata to the repo's own governance files.

## Trace Matrix: Tech Decision → FR / SC

| Decision | Requirement(s) | Principle(s) |
|----------|----------------|--------------|
| Python 3.11 + stdlib `pathlib` / `hashlib` for resolver | FR-002, FR-004, FR-005 | I, VII |
| Pydantic v2 models + JSON Schema mirrors under `contracts/` | FR-004, FR-005, FR-007 | II |
| Deterministic DFS of `@path` with declaration-order preservation | FR-005, SC-001 | I |
| `TEAM_MEMORY_MAX_BYTES = 20 KB` + lint test | FR-007, SC-003 | III |
| Typed `ResolutionDiagnostic` exceptions for missing / cycle | FR-004, SC-004 | I, VI |
| `scope ∈ {team, personal}` label + `effective_for_project_task()` | FR-003, FR-006, SC-002 | II |
| `source_path` + `source_sha256` on every `MemoryEntry` | FR-005 | VII |
| Fresh-clone equivalence test using `anthropic` SDK | SC-001 | I, V |
| Five fixture trees under `tests/.../fixtures/` | FR-004, FR-007, SC-001..SC-004 | V |
| pytest + pytest-bdd | all acceptance scenarios | V |
| Canonical template + `standards/` as kata output | FR-001, FR-002 | VIII |

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  Memory Resolver   │───────│   Team CLAUDE.md   │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Standards Manua…│ │Personal CLAUDE…│ │ Diagnostic Log │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `Memory Resolver` owns the core control flow
for this kata's objective; `Team CLAUDE.md` is the primary collaborator/policy reference;
`Standards Manuals`, `Personal CLAUDE.md`, and `Diagnostic Log` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Deliberately omitted:

- **YAML / TOML front-matter parsing.** The `@path` grammar is a single
  line-level token; regex-free line scan is sufficient. Adding a parser
  would pull in a dependency for no FR coverage.
- **Graph library (e.g. `networkx`).** Cycle detection needs a 15-line DFS
  with a `visiting` set; a third-party library is YAGNI.
- **Runtime hot-reload of memory files.** Out of scope — the spec is about
  startup-time determinism. Hot-reload would need an invalidation strategy
  with no FR calling for it.
- **Automatic rewriting of `CLAUDE.md` to fit the size budget.** Out of
  scope — the kata teaches the *discipline*, not an auto-trimmer.
