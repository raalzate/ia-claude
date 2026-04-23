# Kata 9 — Quickstart

## What you'll build

A `.claude/rules/` layout with YAML-frontmatter path patterns + a
`PathScopedRuleLoader` that activates rules ONLY when the edited file matches.
Unmatched edits cost zero additional tokens — the kata's whole point.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/009_path_rules -v
```

Scenarios:
- single-match: one rule file activates for `foo.test.tsx`.
- multi-overlapping-match: two rules match; lower `precedence` wins; both logged.
- no-match: zero rules activate, zero extra tokens (SC-001 property test).
- invalid-frontmatter: `LoaderDiagnostic code=invalid_frontmatter` (fail loud).
- empty-pattern-list: `LoaderDiagnostic code=empty_pattern_list`.
- oversized-rule-file: warning diagnostic, load still allowed but flagged.

## Inspect a live activation

```bash
python -m katas.009_path_rules.demo --edited-path "src/components/button.test.tsx"
```

Emits `RuleActivationEvent` JSON showing matched rule files, precedence, and
added token cost.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Test-file edit activates testing rules | US1, FR-001 | `single_match/` |
| Unrelated edit → zero rules | US2, SC-001 | `no_match/` |
| New rule file activates only on match | US3 | `new_rule_pattern/` |
| Overlapping patterns resolve by precedence | Edge #1 | `multi_overlap/` |
| Invalid frontmatter fails loud | Edge #3, FR-003 | `invalid_frontmatter/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending testify + tasks.
- [x] Always-on loading anti-pattern defended by zero-activation property test.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection prompt

- Which rule file in this repo's own `.claude/rules/` would you scope vs. keep
  global, and why?
- How does precedence prevent surprise when two rule files cover the same file
  type with conflicting guidance?
