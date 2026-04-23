# Phase 1 Data Model: Path-Scoped Conditional Rules

All entities below are implemented as pydantic v2 models at
`katas/009_path_rules/models.py`. Validation runs on construction; any invalid
payload raises `pydantic.ValidationError` (or the typed
`FrontmatterError` below for frontmatter-specific failures) and the loader
halts. Spec entities map to concrete models 1:1.

## RuleFile

The in-memory representation of a parsed `.claude/rules/<name>.md` file.

| Field | Type | Notes |
|-------|------|-------|
| `path` | `pathlib.Path` | Absolute path to the rule file on disk. |
| `filename` | `str` | Basename (e.g. `testing.md`). Used for lexicographic tiebreak (FR-004). |
| `paths` | `list[PathPattern]` | Non-empty list of glob patterns from frontmatter. |
| `precedence` | `int` | From frontmatter; default `1000` when absent (FR-004, research D-003). |
| `body` | `str` | Markdown body (everything after the closing `---`). |
| `body_byte_size` | `int` | Computed. Used by the "very large rule file" warning diagnostic. |

**Invariants**
- `paths` MUST be a non-empty list; empty raises `FrontmatterError` with
  `reason="paths_empty"` (FR-003, SC-003).
- `precedence` MUST be an integer; non-int raises `FrontmatterError` with
  `reason="precedence_not_int"`.
- `body` MUST NOT be modified after construction — rule bodies are immutable
  for the lifetime of a turn (supports prefix-cache stability, Principle III).
- Constructing a `RuleFile` does NOT inject it into any turn. Activation is
  an explicit loader operation (FR-001, FR-002).

## PathPattern

A single glob pattern declared by a `RuleFile`.

| Field | Type | Notes |
|-------|------|-------|
| `glob` | `str` | The raw pattern, e.g. `"**/*.test.tsx"`. |
| `owning_rule` | `str` | `RuleFile.filename` back-reference for audit. |

**Validation**
- `glob` MUST be a non-empty string; empty or whitespace-only raises
  `FrontmatterError` with `reason="empty_glob"`.
- No regex metacharacters beyond the glob set (`*`, `**`, `?`, `[...]`) are
  rejected at schema time — matching is delegated to
  `pathlib.PurePath.match` / `fnmatch.fnmatchcase` (research D-002).

**Matching rule** (pure function `matcher.match(edited_path, pattern) -> bool`):
1. Normalize `edited_path` separators to `/`.
2. If pattern contains `**`, use `fnmatch.fnmatchcase`.
3. Otherwise use `pathlib.PurePath(edited_path).match(glob)`.
4. Matching is case-sensitive.

## ActiveRuleSet

The deduplicated, ordered collection of `RuleFile`s activated for one turn.
This is what the loader returns to the caller (FR-001, FR-005).

| Field | Type | Notes |
|-------|------|-------|
| `turn_id` | `str` (UUID4) | Correlates with the `MatchingEvent` records for the turn. |
| `edited_file_paths` | `list[str]` | The paths consumed from the turn. Read-only tool targets MUST NOT appear here. |
| `members` | `list[RuleFile]` | Ordered by `precedence` ascending, then `filename` ascending (FR-004). Deduplicated by `filename`. |
| `events` | `list[MatchingEvent]` | Every (edited_path, rule) activation that produced a member. |
| `total_body_bytes` | `int` | Sum of `members[*].body_byte_size`. Reported as a loader diagnostic so large rules are visible (spec edge case: "Very large rule file"). |

**Invariants**
- `members` MAY be empty: that's the zero-activation turn and MUST produce
  zero bytes of additional prompt context (FR-002, FR-006, SC-001).
- `members` MUST NOT contain duplicates — if two edited paths match the same
  rule file, the rule file appears once and both matching events are listed
  in `events`.
- The ordering invariant is asserted in `test_matcher_precedence.py`.

## MatchingEvent

One line of the activation audit log. Serialized as JSONL at
`runs/<session-id>/rule-activation.jsonl`; schema-locked at
`contracts/rule-activation-event.schema.json`.

| Field | Type | Notes |
|-------|------|-------|
| `turn_id` | `str` (UUID4) | Parent `ActiveRuleSet.turn_id`. |
| `timestamp` | `datetime` (UTC, ISO-8601) | Emitted at activation time. |
| `edited_path` | `str` | The turn-edited path that triggered activation. |
| `rule_file` | `str` | `RuleFile.filename`. |
| `matched_pattern` | `str` | The specific `PathPattern.glob` that fired. |
| `precedence` | `int` | Copy of `RuleFile.precedence` for audit without joining. |

**Invariants**
- One `MatchingEvent` per (edited_path, rule_file) pair that matched. A rule
  activated by two edited paths produces two events.
- No model-output / prose field exists on `MatchingEvent` — matches the
  Principle I pattern Kata 1 established.

## FrontmatterError

Exception raised at rule-file load time. Typed so callers can discriminate
reasons without parsing strings.

| Field | Type | Notes |
|-------|------|-------|
| `path` | `pathlib.Path` | The offending file. |
| `reason` | `Literal[...]` | One of the closed set below. |
| `detail` | `str` | Human-readable elaboration for the practitioner. |

Closed reason set:
```
Literal[
  "yaml_parse_error",     # pyyaml raised
  "missing_paths_key",    # frontmatter exists but no `paths` field
  "paths_not_list",       # `paths` value is not a YAML sequence
  "paths_empty",          # `paths: []`
  "empty_glob",           # list entry is an empty string
  "precedence_not_int",   # `precedence` present but not an integer
  "no_frontmatter_fence", # file lacks the opening `---` delimiter
]
```

Traces: FR-003, SC-003.

## LoaderDiagnostic

Non-fatal observations surfaced by the loader alongside the `ActiveRuleSet`
(spec edge cases: very large rule file, pattern matches nothing). Schema at
`contracts/loader-diagnostic.schema.json`.

| Field | Type | Notes |
|-------|------|-------|
| `severity` | `Literal["info", "warning"]` | Warnings are always surfaced; info may be filtered. |
| `code` | `Literal[...]` | See closed set below. |
| `rule_file` | `str \| None` | Filename when the diagnostic pertains to one rule. |
| `message` | `str` | Human-readable. |

Closed code set:
```
Literal[
  "inert_pattern_no_match_in_turn", # FR-006: pattern exists but matched nothing this turn
  "large_rule_body",                # body_byte_size exceeds configured threshold
  "duplicate_filename_seen",        # belt-and-braces — not reachable on a well-formed dir
]
```

## Relationships

```
LoaderSession (implicit, one per turn)
  ├── inputs
  │     ├── edited_file_paths: [str]
  │     └── rule_files_on_disk: [RuleFile]
  ├── output: ActiveRuleSet
  │     ├── members: [RuleFile]          (ordered, deduplicated)
  │     └── events: [MatchingEvent]      (one per match, fanned-out)
  └── diagnostics: [LoaderDiagnostic]
```

## What is deliberately NOT modeled

- Retry / reload during a turn — activation is resolved once at turn start
  (spec edge case "File touched by tool but not edited" is handled by not
  feeding read-only paths into `edited_file_paths`).
- Rule-body token counts — byte size is a sufficient diagnostic proxy and
  avoids a tokenizer dependency (research D-004).
- Per-user overrides — out of scope for the workshop kata.
- Rule dependency / inclusion (`extends:` field) — spec does not mandate it;
  would add a resolution graph we do not need.
