# Phase 0 Research: Headless CI/CD Review with Claude Code CLI

## Decisions

### D-001 — Invoke the Claude Code CLI non-interactively with `-p`, `--output-format json`, `--json-schema`

- **Decision**: The CI workflow calls `claude -p "<prompt>" --output-format
  json --json-schema katas/013_headless_ci_review/schema/review_finding.schema.json`.
  The `-p`/`--print` flag makes the CLI single-shot and non-interactive; the
  `--output-format json` + `--json-schema` pair contractually binds the
  returned payload to a declared shape.
- **Rationale**: This is the exact CLI contract Kata 13 exists to teach
  (Spec FR-001, FR-002). Running the CLI in default TTY mode inside CI would
  block on interactive prompts; omitting `--json-schema` would hand the CLI
  free rein to emit prose, which is the documented anti-pattern.
- **Alternatives considered**:
  - *Anthropic SDK direct call from Python (as in Kata 001).* Rejected: the
    kata's whole pedagogical point is the **headless CLI** integration; using
    the SDK bypasses the lesson.
  - *`--output-format stream-json`.* Rejected: streaming adds parsing state
    machines to the runner for zero benefit — the reviewer emits one
    structured payload per PR.

### D-002 — Pydantic v2 models only downstream of JSON Schema validation

- **Decision**: `ReviewFinding`, `CLIOutputEnvelope`, `CIJob`, and
  `AnnotationPayload` are pydantic v2 models. They are only constructed from
  a dict that has already passed `jsonschema.Draft202012Validator.validate(...)`.
- **Rationale**: Constitution Principle II (NN). The JSON Schema is the
  single authoritative contract (FR-003); pydantic then gives us typed
  attribute access for the mapper. Running pydantic first would hide schema
  drift behind pydantic's coercion rules; running it second (and only if
  schema validation passed) makes the fail-closed gate unambiguous.
- **Alternatives considered**:
  - *pydantic-only validation.* Rejected: pydantic is lenient about extra
    fields and some union shapes, which would let the CLI drift silently —
    direct Principle II violation.
  - *`dataclasses` + manual checks.* Rejected: bespoke validation code is
    exactly what `jsonschema` + pydantic together replace.

### D-003 — Schema validation runs in a dedicated CI step named `validate_review_output`

- **Decision**: The workflow has a distinct step that invokes a tiny Python
  script (`katas/013_headless_ci_review/validator.py`) to validate
  `reviews/<run-id>/raw.json` against the declared schema. If validation
  fails, the step exits non-zero, the mapper step never runs, and the job
  fails with a clear schema-violation error.
- **Rationale**: FR-003 and FR-004 require a **fail-closed** gate on schema
  drift, with **no fallback** to regex parsing. Putting validation in its own
  step (rather than inlining it in the mapper) makes the gate visible in the
  Actions UI and easy to assert against in tests (SC-001).
- **Alternatives considered**:
  - *Validate inside the mapper.* Rejected: couples the fail-closed gate to
    mapper correctness and makes it harder to prove in tests that no
    annotations can escape on a schema miss.
  - *Validate on the CLI side only (trust `--json-schema`).* Rejected: the
    kata explicitly teaches defense-in-depth; a bug in the CLI's schema
    enforcement would otherwise reach production annotations.

### D-004 — Prefer the Checks API for annotations, with `gh api` as the scriptable interface

- **Decision**: The mapper posts annotations using `gh api
  repos/:owner/:repo/check-runs -f ...` against the Checks API. This renders
  as inline annotations on the PR diff and surfaces a distinct CI check (as
  opposed to a cluster of line comments). The `gh` CLI handles auth via the
  Actions-supplied `GITHUB_TOKEN`.
- **Rationale**: The Checks API is the GitHub surface designed for machine-
  generated annotations — it supports `annotations_level`, `path`,
  `start_line`, `end_line`, and a deterministic update model. It avoids
  polluting the PR's human-review conversation and cleanly separates agent
  output from human comments (FR-005).
- **Alternatives considered**:
  - *`gh pr review --comment --body-file ...` with inline `__PATH__:__LINE__`
    markers.* Rejected: requires the mapper to serialize findings into a
    markdown body that GitHub then parses — exactly the kind of prose round-
    trip the kata forbids.
  - *Direct `octokit`/`PyGithub` library.* Rejected: adds a dependency with
    no upside over `gh api` for this single call; `gh` ships pre-installed on
    `ubuntu-latest` runners.
  - *Workflow-commands `::error file=...,line=...::message`.* Rejected:
    those only render in the Actions log, not as inline PR annotations on
    the diff — would miss FR-005.

### D-005 — AST-based lint forbids regex / split-based parsing of CLI stdout

- **Decision**: A test at
  `tests/katas/013_headless_ci_review/lint/test_no_regex_parsing.py` parses
  `katas/013_headless_ci_review/mapper.py` with the `ast` module and fails
  the build if it finds any of: `import re`, `from re import ...`, a
  `.findall` / `.search` / `.match` call, a `str.split` call on a name whose
  provenance is the raw CLI stdout, or an `in` operator where the right-hand
  side is a `str` literal against raw stdout. The mapper is required to
  consume only the schema-validated `dict` (loaded via `json.load` after
  `validator.py` has run).
- **Rationale**: FR-004 and SC-002 demand zero regex/free-form parsing in
  the CI glue. An AST-level test is the only durable defense — comments and
  code reviews drift, but a build-failing lint does not. Mirrors the D-005
  decision in Kata 001.
- **Alternatives considered**:
  - *Code review only.* Rejected: Principle I is absolute; this is exactly
    the drift the kata is designed to defend against.
  - *`ruff`/`flake8` custom rule.* Deferred: layerable later; the AST test is
    sufficient for MVP.

### D-006 — Raw CLI response is always uploaded as a CI artifact

- **Decision**: The workflow uses `actions/upload-artifact@v4` with
  `if: always()` to upload `reviews/<run-id>/raw.json` and
  `reviews/<run-id>/stderr.log`, regardless of whether the job succeeded,
  failed validation, or the CLI exited non-zero.
- **Rationale**: FR-006 and SC-004 require 100% retention of the raw
  response, **including** runs that failed schema validation — so the
  reviewer's actual output is always inspectable post-hoc. Conditional
  upload would make the most interesting failure cases un-debuggable.
- **Alternatives considered**:
  - *Upload only on failure.* Rejected: SC-004 mandates 100%, not "on
    failure"; successful runs still need the artifact for audit trails.
  - *Commit the artifact to a branch.* Rejected: pollutes history and
    defeats the ephemeral-CI-artifact model.

### D-007 — Review prompt template lives in `katas/013_headless_ci_review/review_prompt.md`, referenced by path from the workflow

- **Decision**: The CI YAML passes the prompt via file reference (e.g.
  `claude -p "$(cat katas/013_headless_ci_review/review_prompt.md)" ...` or a
  dedicated CLI flag that accepts a path). The YAML contains no prompt text.
- **Rationale**: FR-007 requires the prompt to be editable without touching
  CI glue or mapper code. Keeping the prompt as a sibling Markdown file makes
  it diffable, reviewable, and swappable in a single-file PR.
- **Alternatives considered**:
  - *Prompt inlined in `ci-review.yml`.* Rejected: direct FR-007 violation;
    every prompt iteration would require a workflow edit.
  - *Prompt in a separate repository pulled via submodule.* Rejected:
    operational complexity with no benefit at workshop scope.

### D-008 — `jsonschema` Python library as the schema validator

- **Decision**: `validator.py` uses `jsonschema.Draft202012Validator` to
  validate the CLI output against `review-finding.schema.json` (wrapped by
  `cli-output-envelope.schema.json`).
- **Rationale**: `jsonschema` is the reference Python implementation, tracks
  Draft 2020-12 (same draft the CLI's `--json-schema` flag accepts), and
  offers `.iter_errors()` so the validator can log *every* violation (not
  just the first) into the retained artifact — supporting audit.
- **Alternatives considered**:
  - *`fastjsonschema`.* Rejected: faster but error messages are terser,
    which is the wrong trade-off for a teaching context.
  - *Pydantic's `TypeAdapter` only.* Rejected per D-002.

### D-009 — Fixtures cover every declared edge case in the spec

- **Decision**: Fixture corpus:
  - `valid_findings.json` — multi-finding happy path.
  - `schema_violation.json` — missing required `line` field → must fail
    closed (US2-AS2, SC-001).
  - `empty_findings.json` — zero findings but schema-valid (FR-008).
  - `zero_changed_files.json` — simulates a PR with only renames/metadata.
  - `oversized_pr.json` — CLI emits a structured oversize signal; workflow
    fails closed with labeled reason (Spec Edge #4, FR-009).
  - `cli_nonzero_exit.sh` — shim that returns exit code 2 and writes to
    stderr; workflow fails closed (Spec Edge #1, FR-009).
- **Rationale**: Each fixture corresponds to one or more acceptance scenarios
  so `/iikit-04-testify` can generate Gherkin with direct `@SC-NNN` /
  `@FR-NNN` tags and the assertion-integrity hashes lock to a known set.
- **Alternatives considered**:
  - *Live CLI fixtures.* Rejected: flaky and quota-consuming. Fixtures are
    the right abstraction because the kata verifies **glue-code behavior**,
    not model output quality.

### D-010 — `gh` CLI over GitHub Checks API (final choice)

- **Decision**: Use `gh api` to POST to `/repos/:owner/:repo/check-runs`.
  The mapper builds an `AnnotationPayload` object, serializes it with
  pydantic's `model_dump()`, and pipes the JSON to `gh api --input -`.
- **Rationale**: See D-004. Documented here as the concluded choice after
  comparing `gh pr review`, direct REST via `curl`, and `PyGithub`. `gh api`
  wins on: (a) pre-installed on ubuntu-latest, (b) handles auth from
  `GITHUB_TOKEN` transparently, (c) accepts JSON on stdin, so the mapper
  doesn't have to string-format bash arguments (avoiding Principle I drift).
- **Alternatives considered**: documented inline in D-004.

## Tessl Tiles

`tessl search "github actions claude cli"` and `tessl search "headless
review"` (run 2026-04-23) returned no tiles covering GitHub Actions
integration with the Claude Code CLI or the Checks API annotation flow.
Closest adjacent hit was a generic CI-lint tile that does not touch agent
output. **No tiles installed for this feature.**

Follow-up: revisit if a community tile specifically for Claude Code headless
mode or for JSON-Schema-gated annotation posting appears. Search terms to
re-try: `claude-code-cli`, `checks-api annotations`, `ci reviewer agent`.
No eval scores recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION from the spec (there were 0) has been
resolved by the decisions above. The only deliberate deferrals — retries,
context-size pre-trimming, custom annotation UI — are documented in `plan.md`
under Complexity Tracking and explicitly rejected to preserve the
fail-closed stance that the Constitution's Principles I and II require.
