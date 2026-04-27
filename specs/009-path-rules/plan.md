# Implementation Plan: Path-Scoped Conditional Rules

**Branch**: `009-path-rules` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/009-path-rules/spec.md`

## Summary

Build a Python kata module that loads rule files from `.claude/rules/` **only
when** at least one file edited in the current turn matches a glob declared in
that rule file's YAML frontmatter. The `PathScopedRuleLoader` parses each rule
file's frontmatter into a pydantic `RuleFile`, matches edited paths against
declared `paths` patterns, and returns a deterministically ordered
`ActiveRuleSet` plus a per-turn `MatchingEvent` audit log. Turns with no
matching edits return an empty set and add **zero** tokens beyond the baseline
prompt (SC-001 proxy). Invalid frontmatter raises `FrontmatterError` at load
time — never silently skipped (SC-003). Delivered under Constitution v1.3.0
principles II (Schema-Enforced Boundaries), III (Context Economy), V (TDD),
VII (Provenance & Self-Audit), VIII (Mandatory Documentation).

This kata extends the idea introduced by Kata 8 (CLAUDE.md memory resolver):
Kata 8 resolved *static* memory sources at session start; Kata 9 resolves
*edit-scoped* memory sources per turn. Kata 8's plan was a stub at the time of
writing, so this kata is designed standalone — if/when Kata 8 defines a shared
`MemoryResolver` interface, `PathScopedRuleLoader` can plug in as an
edit-conditional source without changing its contract.

## Technical Context

**Language/Version**: Python 3.11+ (shared workshop baseline — Kata 1 plan).
**Primary Dependencies**:
- `pydantic` v2 — frontmatter schema enforcement on `RuleFile`
  (Constitution II). Invalid frontmatter raises at load, never "best-effort".
  Traces: FR-003, SC-003.
- `pyyaml` — YAML frontmatter parser. **New dep for the workshop**; justified
  because Python stdlib has no YAML parser, the `.claude/rules/*.md`
  frontmatter convention is YAML, and every realistic rule file the kata
  fixtures must parse is YAML. `pyyaml` is the ubiquitous choice
  (Ansible/Helm/pre-commit all use it), which makes the kata runnable on any
  workshop laptop without a bespoke mini-parser. Pinned `safe_load` only —
  tag resolution is disabled so frontmatter cannot execute code. Traces:
  FR-001, FR-003.
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).
- `anthropic` SDK (optional, for one gated integration test) — sends a short
  prompt while simulating an edit to a matching file and asserts the matching
  rule's body appears in the composed context window. Default test run stubs
  the SDK (same pattern as Kata 1); live run behind `LIVE_API=1`. Traces:
  FR-001, SC-002.

**Storage**: Local filesystem only. Rule files live at
`katas/009_path_rules/fixtures/.claude/rules/*.md` for tests, and at
`.claude/rules/*.md` in the host repo at run time. Per-turn audit entries are
emitted as JSONL at `runs/<session-id>/rule-activation.jsonl` (same shape as
Kata 1's event log — append-only, one line per `MatchingEvent`). Traces:
FR-005, SC-004.

**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit tests; JSON Schema validation for contract tests. A token-cost accounting
helper (not a real tokenizer — counts bytes of the composed prompt under the
loader's control) asserts the **zero-activation** property: for a turn that
edits only non-matching files, the byte delta against a baseline prompt is 0
(SC-001 proxy; documented in `research.md` D-004).

**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.

**Project Type**: Single project — kata module under
`katas/009_path_rules/`, tests under `tests/katas/009_path_rules/`. Matches
the layout Kata 1 established.

**Performance Goals**: Not latency-bound. Loader over a fixture directory of
≤ 20 rule files completes in < 50 ms locally; acceptance suite finishes in
< 5 s.

**Constraints**:
- Frontmatter parse errors MUST raise `FrontmatterError` with the offending
  file path and failure reason (FR-003, SC-003) — no silent skip path exists
  in source.
- Turns that edit zero files, or only non-matching files, MUST produce an
  empty `ActiveRuleSet` and MUST NOT concatenate any rule body into the
  prompt context (FR-002, FR-006, SC-001).
- Overlap precedence MUST be deterministic: lower integer `precedence` wins,
  ties broken by filename lexicographic ascending (FR-004). Documented in
  `research.md` D-003.
- Domain-specific rules MUST live under `.claude/rules/` only — a contract
  test asserts no domain rules leak into the host repo's `CLAUDE.md`
  (FR-007, anti-pattern defense).
- Read-only tool calls MUST NOT feed into the `edited_file_path` set the
  loader consumes (spec edge case: "File touched by tool but not edited").

**Scale/Scope**: One kata, ~250–400 LOC implementation + comparable test
code; one README; fixture corpus: 6 scenarios (single-match,
multi-overlapping-match, no-match, invalid-frontmatter, empty-pattern-list,
very-large-rule-file).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Matching is a pure glob comparison (`pathlib.PurePath.match` + `fnmatch.fnmatchcase`). Precedence order is fully specified (int precedence → filename). No branch of the loader reads model prose. |
| II. Schema-Enforced Boundaries (NN) | `RuleFile`, `MatchingEvent`, loader diagnostics are pydantic v2 models. Every JSON artifact has a `$id kata-009` JSON Schema contract. Frontmatter validation runs via `model_validate`. |
| III. Context Economy | Headline principle for this kata. Zero-activation property test (SC-001 proxy) asserts byte-level parity between baseline and no-match turns. Rule bodies are appended as a dynamic suffix only when a match occurs — the stable prefix is untouched so prefix caches hold. |
| IV. Subagent Isolation | Not applicable — this kata runs a single loader, not a multi-agent handoff. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code; tasks will cite test-spec IDs. Red-green hash-locked via `.specify/context.json`. |
| VI. Human-in-the-Loop | `FrontmatterError` halts load and surfaces an explicit human-readable error; the practitioner fixes the file rather than the loader guessing. Matches the Constitution's "fail loud" stance. |
| VII. Provenance & Self-Audit | `MatchingEvent` records per-activation provenance: (turn_id, edited_path, rule_file, matched_pattern). Emitted as append-only JSONL, same shape as Kata 1 — replayable offline. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function in the loader will carry a *why* comment tied to FR-001/-002/-003 or the anti-pattern it defends against. A single `notebook.ipynb` produced at `/iikit-07-implement` is the Principle VIII deliverable: it explains the kata, results, every Claude architecture concept exercised, the architecture walkthrough, applied patterns + principles, practitioner recommendations, the contract details, run cells, and the reflection. No separate `README.md`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/009-path-rules/
  plan.md              # this file
  research.md          # Phase 0 output: D-001..D-006 + Tessl discovery note
  data-model.md        # Phase 1 output: RuleFile, PathPattern, ActiveRuleSet,
                       # MatchingEvent, FrontmatterError
  quickstart.md        # Phase 1 output: install, fixture run, scenario→spec map,
                       # §Kata Completion Standards checklist
  contracts/           # Phase 1 output: JSON Schemas, $id kata-009
    rule-file-frontmatter.schema.json
    rule-activation-event.schema.json
    loader-diagnostic.schema.json
  checklists/
    requirements.md    # already present — output of /iikit-01
  tasks.md             # generated by /iikit-05-tasks
  # (kata narrative lives in katas/.../notebook.ipynb — no spec-side README)
```

### Source Code (repository root)

```text
katas/
  009_path_rules/
    __init__.py
    loader.py            # PathScopedRuleLoader: parse → match → activate
    frontmatter.py       # YAML frontmatter parser + FrontmatterError
    models.py            # pydantic models: RuleFile, PathPattern,
                         #   ActiveRuleSet, MatchingEvent
    matcher.py           # glob matching + precedence resolution
    audit.py             # JSONL writer for MatchingEvent (mirrors Kata 1 events.py)
    runner.py            # CLI entrypoint: python -m katas.009_path_rules.runner
    fixtures/            # shipped reference rule files used by quickstart demo
      .claude/rules/
        testing.md
        api-conventions.md
    notebook.ipynb       # Principle VIII deliverable — kata narrative + Claude architecture certification concepts (written during /iikit-07)

tests/
  katas/
    009_path_rules/
      conftest.py
      features/          # Gherkin files produced by /iikit-04-testify
        path_rules.feature
      step_defs/
        test_path_rules_steps.py
      unit/
        test_frontmatter_parse.py        # FR-003 / SC-003
        test_matcher_precedence.py       # FR-004
        test_zero_activation_property.py # FR-002 / FR-006 / SC-001 proxy
        test_audit_log_shape.py          # FR-005 / SC-004
      contract/
        test_schema_rule_file_frontmatter.py
        test_schema_rule_activation_event.py
        test_schema_loader_diagnostic.py
      integration/
        test_live_rule_injection.py      # gated by LIVE_API=1; anthropic SDK
      fixtures/
        rules/
          single_match/.claude/rules/testing.md
          multi_overlap/.claude/rules/{testing.md,tsx-style.md}
          no_match/.claude/rules/api.md
          invalid_frontmatter/.claude/rules/broken.md
          empty_patterns/.claude/rules/empty.md
          very_large/.claude/rules/huge.md
```

**Structure Decision**: Single-project layout. Kata 9 is a sibling package
under `katas/` alongside Kata 1, following the FDD-per-kata cadence the
Constitution mandates. Tests mirror the source tree. Runs write to
`runs/<session-id>/` (gitignored). No cross-kata imports; if Kata 8 later
publishes a `MemoryResolver` protocol, `PathScopedRuleLoader` can implement
it in a follow-up PR without restructuring.

## Requirement Traceability

| Tech decision | Serves |
|---------------|--------|
| pydantic v2 `RuleFile` | FR-003, SC-003, Principle II |
| pyyaml `safe_load` | FR-001, FR-003 |
| `pathlib.PurePath.match` + `fnmatch.fnmatchcase` | FR-001, FR-004 |
| Int `precedence` tiebreak on filename asc | FR-004 |
| JSONL `MatchingEvent` log | FR-005, SC-002, SC-004, Principle VII |
| Zero-activation byte-delta test | FR-002, FR-006, SC-001, Principle III |
| `FrontmatterError` at load | FR-003, SC-003, Principle VI |
| Host-repo `CLAUDE.md` leak test | FR-007 |
| AST-free pure matching module | Principle I |

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│    Rule Loader     │───────│    Path Matcher    │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│   Rule Files   │ │ Activation Log │ │Rule Diagnostic…│
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `Rule Loader` owns the core control flow
for this kata's objective; `Path Matcher` is the primary collaborator/policy reference;
`Rule Files`, `Activation Log`, and `Rule Diagnostic Sink` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Adding `pyyaml` is the only new dependency over the Kata 1
baseline; its justification is captured in the Technical Context and in
`research.md` D-001. Intentionally omitted: hot-reload of rule files during a
turn (out of scope — spec scopes activation to per-turn resolution), glob
compilation cache (premature), multi-repo rule discovery.
