# Phase 0 Research: Path-Scoped Conditional Rules

## Decisions

### D-001 — Use `pyyaml` (`safe_load`) for frontmatter parsing

- **Decision**: Parse the YAML frontmatter block of each `.claude/rules/*.md`
  file with `yaml.safe_load` from `pyyaml`. The frontmatter is the
  standard `---\n<yaml>\n---\n<body>` convention used by Jekyll, Hugo, Zola,
  obsidian, and by the existing `.claude/` ecosystem.
- **Rationale**: Python's stdlib has no YAML parser. The frontmatter fields
  the kata depends on (`paths: list[str]`, optional `precedence: int`) are
  real YAML, not ad-hoc key/value, so a bespoke mini-parser would either
  accept invalid YAML (silent failure — violates FR-003 / SC-003) or
  reinvent `pyyaml`. `pyyaml` is the ubiquitous Python YAML library
  (Ansible, Helm charts via Jinja, pre-commit, mkdocs, GitHub Actions
  workflow parsers) so the kata is runnable on any workshop laptop. Using
  `safe_load` — not `load` — disables tag resolution: frontmatter cannot
  instantiate arbitrary Python objects. Traces: FR-001, FR-003, SC-003,
  Constitution Principle II.
- **Alternatives considered**:
  - *Hand-rolled `key: value` parser.* Rejected: silently misparses lists
    and quoted strings; fails FR-003's "invalid frontmatter surfaces an
    explicit error" requirement because the handroll has no canonical
    notion of "invalid".
  - *`ruamel.yaml`.* Rejected: superior round-tripping is irrelevant here
    (we never rewrite rule files); adds install size without pedagogical
    value.
  - *TOML frontmatter via `tomllib` (stdlib).* Rejected: TOML is not the
    convention the `.claude/rules/` ecosystem uses; spec explicitly cites
    YAML frontmatter.

### D-002 — Matching via `pathlib.PurePath.match` with `fnmatch.fnmatchcase` fallback

- **Decision**: `RuleFile` activation is driven by
  `pathlib.PurePath(edited_path).match(pattern)` for each glob pattern
  declared in its frontmatter. For patterns containing `**` recursion, we
  fall through to `fnmatch.fnmatchcase(edited_path, pattern)` after
  normalizing path separators to `/`. Matching is case-sensitive so
  `Button.test.tsx` and `button.test.tsx` do not collide.
- **Rationale**: `PurePath.match` covers `*.ext` and shallow segment globs
  directly — zero new dependency beyond stdlib. `**` recursive globs (the
  spec's canonical example `**/*.test.tsx`) are not fully supported by
  `PurePath.match` on Python 3.11, so we normalize and delegate to
  `fnmatch.fnmatchcase` which handles recursive wildcards after the
  convention is reduced to flat string match. Both are pure functions,
  satisfying Principle I (no probabilistic branching) and making matching
  unit-testable without filesystem I/O. Traces: FR-001, FR-004.
- **Alternatives considered**:
  - *`pathspec` (git-wildmatch).* Rejected as YAGNI: we don't need `.gitignore`
    negation semantics and the workshop keeps its dependency list minimal.
  - *Compile each glob to a regex with `re`.* Rejected: regex-on-path would
    invite the same "prose matching" anti-pattern Kata 1 forbids, even
    though paths are structured — the `fnmatch`/`PurePath` pair is the
    idiomatic Python choice.

### D-003 — Deterministic overlap precedence: int `precedence` ascending, then filename lexicographic ascending

- **Decision**: When more than one rule file's patterns match the same
  edited path, the `ActiveRuleSet` orders them by:
  1. `precedence` frontmatter field, integer, **lower wins**. Default when
     the field is absent is `1000` so explicit declarations always outrank
     defaults.
  2. Tiebreak: filename in lexicographic ascending order (`api.md` before
     `testing.md`).
- **Rationale**: Spec FR-004 mandates deterministic, documented resolution.
  Integer precedence gives authors explicit control; the filename tiebreak
  guarantees ordering even when two files share the same precedence. Two
  runs over the same edits produce the exact same ordered `ActiveRuleSet`,
  matching Constitution Principle I. Traces: FR-004.
- **Alternatives considered**:
  - *Alphabetical only.* Rejected: brittle — renaming a file silently
    reshuffles rule priority.
  - *Most-specific-pattern wins.* Rejected: "specificity" is ambiguous for
    globs and not machine-checkable without a custom comparator. An
    explicit integer is cheaper to teach.
  - *File mtime / declaration order.* Rejected: mtime changes across
    checkouts; declaration order implies a registry we deliberately don't
    keep.

### D-004 — Zero-activation property asserted via byte-delta of composed prompt

- **Decision**: A dedicated unit test
  (`test_zero_activation_property.py`) composes the baseline system prompt
  with the loader injected as a no-op (empty `.claude/rules/` dir) and
  then with the loader resolving for a path that matches **none** of the
  fixture rules. Both composed prompt strings are byte-compared; the test
  fails if they differ by a single byte. This is the SC-001 proxy.
- **Rationale**: A real tokenizer (tiktoken-style) introduces model-coupled
  variance and a binary dependency that hides the point. Byte-identity is a
  strictly stronger guarantee than token-count parity: if the bytes match,
  the tokens match. Traces: FR-002, FR-006, SC-001, Constitution Principle
  III.
- **Alternatives considered**:
  - *Token count via `tiktoken` or `anthropic.tokenizers`.* Rejected:
    tokenizer version drift causes flaky tests that teach the wrong lesson.
  - *Manual inspection during review.* Rejected: not automatable, violates
    the TDD mandate.

### D-005 — Explicit `FrontmatterError` at load time, never a skip

- **Decision**: Invalid frontmatter (non-YAML, missing `paths` key,
  non-list `paths`, empty `paths` list, non-string glob entries) raises a
  typed `FrontmatterError(path, reason)` at load. The loader does not wrap
  the exception in a warning; the caller is expected to surface it to the
  practitioner.
- **Rationale**: Spec FR-003 and SC-003 both make "silent skip" the
  anti-pattern. Halting on first invalid file is the defendable choice; it
  mirrors Kata 1's `MalformedToolUse` pattern. Traces: FR-003, SC-003,
  Constitution Principle VI.
- **Alternatives considered**:
  - *Log warning and skip.* Rejected as the literal anti-pattern.
  - *Collect all errors and raise at end.* Deferred — possible future
    enhancement, but first-error-halt keeps the error message pinpoint.

### D-006 — Single-project layout, mirrors Kata 1

- **Decision**: Kata 9 sits at `katas/009_path_rules/` with matching tests
  under `tests/katas/009_path_rules/`. No shared library between katas
  yet.
- **Rationale**: The Constitution's FDD cadence rewards isolated,
  independently-gradeable kata packages. Kata 8 (which arguably wants the
  same `MemoryResolver` interface) hasn't shipped its plan yet; introducing
  a shared abstraction now would violate YAGNI and create coupling that a
  later refactor can introduce cleanly. Traces: Constitution Development
  Workflow FDD clause.
- **Alternatives considered**:
  - *Shared `katas/_memory/` package.* Rejected: premature until Kata 8
    lands.
  - *Separate repo per kata.* Rejected for the same reasons Kata 1 cited.

## Tessl Tiles

`tessl search yaml frontmatter` (intent: find a pre-built YAML-frontmatter
loader tile) and `tessl search path glob rules` (intent: find a path-scoped
rule resolver) — **no matching tiles returned** as of 2026-04-23. Closest hits
were unrelated (static-site generator templates, cybersecurity path-traversal
checks). **No tiles installed for this feature.**

Follow-up: revisit at Kata 10 plan time if a community tile for
`.claude/rules/` resolution later appears (search terms:
`claude-rules-loader`, `anthropic-memory-frontmatter`). No eval scores
recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION from the spec (there were 0) has been
resolved by the decisions above. Open coordination items that are *not*
blockers:

- If Kata 8 publishes a `MemoryResolver` protocol, refactor
  `PathScopedRuleLoader` to implement it — tracked as a post-MVP task, not a
  Phase-0 unknown.
