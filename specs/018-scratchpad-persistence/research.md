# Phase 0 Research: Transactional Memory Preservation via Scratchpad

## Decisions

### D-001 — Fixed section set with YAML-frontmatter + markdown body

- **Decision**: `investigation-scratchpad.md` has YAML frontmatter + fixed
  sections (`## Map`, `## Findings`, `## Open Questions`, `## Decisions`,
  `## Conflicts`). Each finding is a numbered list item with typed metadata
  (id, timestamp, category, evidence, source_ref) rendered from the structured
  source of truth.
- **Rationale**: Machine-parseable AND human-readable. Matches conventions
  in related Claude Code workflows.
- **Alternatives**: JSON-only (machine-parseable but un-skimmable), plain
  markdown (skimmable but un-parseable) — rejected.

### D-002 — Append-only writer API with flock

- **Decision**: `ScratchpadWriter.add_finding(...)`, `.note_conflict(...)`,
  `.resolve_open_question(...)` are the ONLY mutation paths. File-level
  `fcntl.flock` serializes concurrent writers on the same pad.
- **Rationale**: Concurrent edits is the pad's worst failure mode (Edge #4).
  flock is adequate for workshop scope.
- **Alternatives**: SQLite WAL — rejected (complexity).

### D-003 — Compaction threshold 55%

- **Decision**: `ContextAnchor` construction fires when
  `session_usage_ratio >= 0.55`. Anchor = (a) `## Decisions` verbatim, (b)
  `## Open Questions` verbatim, (c) a 2-line summary of `## Map`.
- **Rationale**: Same threshold as Kata 11; consistency across katas.
  Keeping anchor small keeps post-resume prefix-cacheable.

### D-004 — Rotation at 100 KB

- **Decision**: `MAX_SCRATCHPAD_BYTES = 100_000`. Rotation: renames current
  pad to `<name>.<iso-date>.md`, starts a fresh one whose frontmatter
  `prior_pad: <rotated-name>`. Post-rotation test asserts cap never exceeded.
- **Rationale**: 100 KB is the rough ceiling before markdown readers slow
  down and before the pad dominates the anchor.

### D-005 — Conflict routing

- **Decision**: Findings that contradict an earlier finding land in
  `## Conflicts` with cross-refs to both finding ids. Never auto-resolved
  (aligns with Kata 20 provenance philosophy).
- **Rationale**: Preserves audit; defers resolution to human.

### D-006 — Parse-round-trip validation

- **Decision**: Every write is followed by a parse-round-trip check — write,
  then read back into a `Scratchpad` model, assert equivalence. Drift raises
  `ScratchpadSchemaError`.
- **Rationale**: Detects markdown rendering bugs immediately; guarantees the
  pad is loadable at session-start.

## Tessl Tiles

`tessl search scratchpad` / `tessl search memory` — no applicable tile.
None installed.

## Unknowns

None.
