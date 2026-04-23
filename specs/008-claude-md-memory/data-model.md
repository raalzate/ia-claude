# Phase 1 Data Model: Hierarchical Memory Orchestration in CLAUDE.md

All entities below are implemented as pydantic v2 models at
`katas/008_claude_md_memory/models.py`. Each has a corresponding JSON Schema
mirror under `specs/008-claude-md-memory/contracts/`. Validation runs on
construction; any invalid payload raises `pydantic.ValidationError` and the
resolver halts — there is no silent best-effort path.

## Scope (Literal type)

```
Literal["team", "personal"]
```

- `team` — loaded from the repo-committed project memory file
  (`.claude/CLAUDE.md` or root `CLAUDE.md`) and everything it `@path`-pulls.
- `personal` — loaded from `~/.claude/CLAUDE.md` (or `$CLAUDE_HOME/CLAUDE.md`
  for testability; tests redirect HOME rather than touching the real user
  profile).

## PathReference

One resolved `@path` edge.

| Field | Type | Notes |
|-------|------|-------|
| `raw` | `str` | Exact token as written in the source, e.g. `@./standards/coding-style.md`. |
| `resolved_path` | `str` (absolute POSIX) | Canonical absolute path after `realpath` normalization. |
| `parent_path` | `str` (absolute POSIX) | Absolute path of the file that declared this `@path`. |
| `declaration_line` | `int` (≥ 1) | 1-indexed line number within the parent where the reference appears. Used in diagnostics. |
| `scope` | `Scope` | Inherits scope from the root file (team references pull team entries; personal references pull personal entries). |

**Invariants**
- `resolved_path` is always absolute and `realpath`-normalized so cycle
  detection compares canonical identities (a reference via `./foo` and one
  via `../dir/foo` resolve to the same node).
- `raw` must begin with `@` followed by a path token; models that fail this
  check raise on construction.

## MemoryEntry

One resolved memory file's content, captured at a DFS visit.

| Field | Type | Notes |
|-------|------|-------|
| `source_path` | `str` (absolute POSIX) | Canonical path of the file this entry came from. |
| `source_sha256` | `str` (64 hex chars) | SHA-256 of the file contents as read. Principle VII provenance anchor. |
| `source_bytes` | `int` (≥ 0) | Byte length of the file contents. Used by the size-budget accountant. |
| `scope` | `Scope` | `team` or `personal`. |
| `declaration_order` | `int` (≥ 0) | DFS visit index. Output list is sorted by this field for determinism. |
| `content` | `str` | File contents verbatim, line-ending-preserved. |
| `references` | `list[PathReference]` | `@path` tokens found in this file, in declaration order. |
| `rule_keys` | `list[str]` | Structured rule identifiers extracted from headings (e.g. `"package-manager"`, `"indent-style"`). Used by the team-vs-personal precedence logic. Empty list is valid. |

**Invariants**
- `source_sha256` is computed inside the resolver (not trusted from outside).
- `declaration_order` is unique within one `ResolvedMemory`.
- The same `source_path` appearing twice (diamond-shaped `@path` graph) MUST
  produce exactly one `MemoryEntry` — the first DFS visit wins; subsequent
  visits are recorded as diagnostics of kind `duplicate_reference` but do
  not duplicate content.

## ResolutionDiagnostic

Structured record of any non-fatal observation or the payload of a fatal
exception.

| Field | Type | Notes |
|-------|------|-------|
| `kind` | `Literal["missing_target", "circular_reference", "unreadable_target", "oversize_memory", "duplicate_reference", "personal_overridden_by_team"]` | Closed enum. |
| `severity` | `Literal["error", "warning", "info"]` | `error` kinds raise; `warning` / `info` are appended to `ResolvedMemory.diagnostics`. |
| `message` | `str` | Human-readable one-liner. |
| `reference` | `PathReference \| None` | The offending edge, when applicable. |
| `cycle_path` | `list[str] \| None` | For `circular_reference`: the ordered list of absolute paths forming the cycle, closed (first == last). |
| `bytes_observed` | `int \| None` | For `oversize_memory`: actual aggregated team size. |
| `bytes_budget` | `int \| None` | For `oversize_memory`: `TEAM_MEMORY_MAX_BYTES`. |
| `conflicting_rule_key` | `str \| None` | For `personal_overridden_by_team`: the rule key that was dropped from the personal scope. |

**Severity-to-exception mapping** (raised by `MemoryResolver.resolve()`):
- `missing_target` → `MissingReferenceError`
- `circular_reference` → `CircularReferenceError`
- `unreadable_target` → `UnreadableReferenceError`
- `oversize_memory` → `OversizeMemoryError`
- `duplicate_reference` → warning, recorded in `diagnostics`, no raise
- `personal_overridden_by_team` → info, recorded in `diagnostics`, no raise

All four exception classes inherit from `MemoryResolutionError` and expose
the diagnostic at `err.diagnostic`.

## ResolvedMemory

Output of `MemoryResolver.resolve()`. The single root aggregate.

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `Literal["1.0"]` | Bump on contract change. |
| `project_root` | `str` (absolute POSIX) | Canonical repo root used for relative resolution. |
| `entries` | `list[MemoryEntry]` | Sorted by `declaration_order`. Immutable after construction. |
| `diagnostics` | `list[ResolutionDiagnostic]` | Non-fatal observations, ordered by emission. |
| `team_bytes_total` | `int` (≥ 0) | Aggregated `source_bytes` across `scope == "team"` entries. |
| `team_bytes_budget` | `int` (≥ 0) | Value of `TEAM_MEMORY_MAX_BYTES` at resolve time. |
| `resolved_at` | `datetime` (UTC) | Populated at construction. |

**Invariants**
- `entries` is non-empty (at minimum the root `CLAUDE.md` must exist).
- `entries` is sorted by `declaration_order`; ties are impossible by
  construction.
- `team_bytes_total <= team_bytes_budget`; equality is permitted, strict
  greater raises `OversizeMemoryError` before this object is constructed.
- Serializing two `ResolvedMemory` instances built from identical source
  trees with `model_dump_json(indent=2, sort_keys=True)` MUST produce
  byte-identical output. This is the operational face of FR-005 / SC-001.

### Derived view — `effective_for_project_task()`

A method, not a separate persisted model:

```
def effective_for_project_task(self) -> list[MemoryEntry]:
    """
    Returns the subset of entries that govern project work:
      - all team entries (in declaration order), AND
      - personal entries whose rule_keys do NOT collide with any team entry's
        rule_keys. Dropped personal entries are recorded as
        ResolutionDiagnostic(kind="personal_overridden_by_team", ...).
    SC-002, FR-003, FR-006.
    """
```

The method is a deterministic pure function of `self.entries`; no I/O.

## Relationships

```
ResolvedMemory
  ├── entries: [MemoryEntry]          (sorted by declaration_order)
  │     └── references: [PathReference]
  ├── diagnostics: [ResolutionDiagnostic]
  ├── team_bytes_total, team_bytes_budget   (Principle III)
  └── project_root, resolved_at, schema_version
```

## What is deliberately NOT modeled

- **Runtime memory hot-reload / watchers.** Out of scope; spec targets
  startup-time determinism.
- **Automatic memory-trimming agent.** The kata teaches the size discipline;
  teaching an auto-trimmer would dilute the anti-pattern defense.
- **Per-tool scope (`session`, `workspace`, etc.).** Spec recognizes two
  scopes only: team and personal. Future katas may extend.
- **Hash chains / Merkle structure across entries.** `source_sha256` per
  entry is sufficient provenance for this kata.
