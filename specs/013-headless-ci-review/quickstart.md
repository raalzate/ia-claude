# Kata 13 — Quickstart

## What you'll build

A `.github/workflows/ci-review.yml` that runs
`claude -p "<review prompt>" --output-format json --json-schema <schema>` on
every PR, validates the JSON against `cli-output-envelope.schema.json` (fails
closed on drift), and posts each `ReviewFinding` as an inline annotation via
the GitHub Checks API. Raw stdout + stderr retained as artifacts for 100% of
runs.

## Install

```bash
pip install -e ".[dev]"
# Also install the Claude Code CLI locally for simulation:
#   npm i -g @anthropic-ai/claude-code   # or follow vendor instructions
```

## Local dry-run

```bash
# Simulate what the workflow does
python -m katas.013_headless_ci_review.simulate \
  --pr-fixture tests/katas/013_headless_ci_review/fixtures/pr_normal.diff \
  --schema specs/013-headless-ci-review/contracts/cli-output-envelope.schema.json
```

Outputs the would-be annotation payload set and asserts the CLI output
validates against the envelope schema.

## Fixture tests

```bash
pytest tests/katas/013_headless_ci_review -v
```

Includes:
- AST lint on `mapper.py` fails if it uses `re.findall`, `str.split`, or
  otherwise touches raw stdout (FR-004, SC-002).
- Schema-violation fixture verifies the workflow step exits non-zero.
- Empty-findings fixture verifies the job succeeds with zero annotations.
- Oversized-PR fixture verifies the job handles the context-limit case.

## Simulate the full workflow in a PR

```bash
# After committing .github/workflows/ci-review.yml, push a test PR.
# Check the Actions tab: the 'ci-review' job runs, validates, and (on success) posts inline annotations.
gh pr checks <pr-number>
```

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Valid findings → inline annotations | US1, SC-003 | `pr_normal.diff` |
| Schema violation → job fails | US2, SC-001 | `cli_output_malformed.json` |
| Empty findings → job succeeds | Edge #3 | `pr_no_issues.diff` |
| Oversized PR | Edge #4 | `pr_oversized.diff` |
| CLI non-zero exit | Edge #1 | `cli_crashed.json` |
| Mapper never touches raw stdout | FR-004, SC-002 | AST lint |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Anti-pattern (free-form/regex parsing) defended by AST lint.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- What's the cheapest test you can add that catches regressions in the
  prompt template?
- If you swap the review prompt, do any CI glue scripts change? Why not?
