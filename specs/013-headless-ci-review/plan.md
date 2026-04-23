# Implementation Plan: Headless CI/CD Review with Claude Code CLI

**Branch**: `013-headless-ci-review` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/013-headless-ci-review/spec.md`

## Summary

Wire a deterministic agentic reviewer into the repository's CI/CD pipeline by
invoking the Claude Code CLI (`claude -p "<prompt>" --output-format json
--json-schema <schema>`) non-interactively on every pull request. The CLI's
structured JSON payload is validated against a declared JSON Schema before any
downstream step consumes it; on schema drift or non-zero CLI exit the job fails
closed and posts no annotations. A thin Python mapper reads the schema-
validated payload and emits inline annotations via GitHub's Checks API (or
`gh api` as the simpler fallback). The raw CLI response (stdout and stderr) is
retained as a CI artifact for 100% of runs, including failures. Delivered
under Constitution v1.3.0 principles I (Determinism, NON-NEGOTIABLE),
II (Schema-Enforced Boundaries, NON-NEGOTIABLE), and VIII (Mandatory
Documentation, NON-NEGOTIABLE), plus the Development Workflow clause that
recommends a deterministic automated reviewer per PR.

## Technical Context

**Language/Version**: Python 3.11+ for the review-mapper script and the
schema-validation gate. GitHub Actions YAML drives orchestration; no Python
beyond the mapper is required on the runner.

**Primary Dependencies**:
- `claude` CLI (Claude Code) installed on the CI runner — sole source of the
  JSON-structured review payload. Invoked exclusively with `-p` (non-
  interactive) and `--output-format json --json-schema <path>` (FR-001, FR-002).
- `pydantic` v2 — `ReviewFinding`, `CLIOutputEnvelope`, `AnnotationPayload`
  models parse the CLI output after JSON-Schema validation (Principle II,
  FR-003).
- `jsonschema` (Python) — Draft 2020-12 validator used by the dedicated
  `validate_review_output` step to fail closed on drift (FR-003, FR-004,
  SC-001).
- `gh` CLI + GitHub Actions built-in `GITHUB_TOKEN` — annotation delivery via
  the Checks API (preferred) or `gh api repos/:owner/:repo/check-runs` as a
  scriptable fallback (FR-005). No third-party PR-comment library.
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).

**Storage**: CI runner filesystem only.
- `reviews/<run-id>/raw.json` — the raw CLI stdout, uploaded as a workflow
  artifact for 100% of runs (FR-006, SC-004).
- `reviews/<run-id>/stderr.log` — raw stderr, same retention policy.
- No database; schema-validated findings are piped straight into annotation
  payloads and discarded after the job ends.

**Testing**:
- `pytest` + `pytest-bdd` for acceptance scenarios against fixture CLI outputs.
- AST-based lint at `tests/katas/013_headless_ci_review/lint/test_no_regex_parsing.py`
  proves `katas/013_headless_ci_review/mapper.py` never calls `re.findall`,
  `re.search`, `str.split`, or iterates over raw stdout — the mapper MUST go
  through the schema-validated dict (FR-004, SC-002).
- Fixture corpus: `valid_findings.json`, `schema_violation.json`,
  `empty_findings.json`, `zero_changed_files.json`, `oversized_pr.json`, plus a
  `cli_nonzero_exit.sh` shim that exits with code 2 and writes to stderr.

**Target Platform**: GitHub Actions (ubuntu-latest) for CI; developer
macOS/Linux for local simulation via `act` or direct invocation of the mapper
against recorded CLI output. No server deployment.

**Project Type**: Single project — one kata package under
`katas/013_headless_ci_review/` with its own tests at
`tests/katas/013_headless_ci_review/` and one workflow file under
`.github/workflows/ci-review.yml`.

**Performance Goals**: Not latency-bound. The CI job's non-CLI overhead
(validation + annotation mapping) completes in under 5 seconds per PR against
fixtures. Wall-clock for the CLI itself is dominated by the model call and is
out of scope.

**Constraints**:
- Zero `re.findall` / `re.search` / `str.split` / substring slicing over the
  raw CLI stdout anywhere downstream — enforced by the AST lint (FR-004,
  SC-002).
- Schema validation runs **before** pydantic parsing; a schema violation exits
  the job non-zero without touching the mapper (FR-003, FR-004).
- Review prompt template lives at
  `katas/013_headless_ci_review/review_prompt.md` and is referenced by the
  workflow via `--system-prompt-file` (or equivalent CLI flag); the workflow
  YAML MUST NOT inline the prompt (FR-007).
- Raw CLI response is uploaded via `actions/upload-artifact@v4` regardless of
  job outcome (`if: always()`), enforcing FR-006 / SC-004.
- Zero-changed-files PRs MUST produce a schema-valid empty findings set; the
  mapper's empty-list branch posts zero annotations and exits 0 (FR-008).
- Non-zero CLI exit OR oversized-context detection MUST fail the job with a
  labeled reason; partial annotations are forbidden (FR-009).

**Scale/Scope**: One kata, ~200–400 LOC of Python (mapper + validator +
lint test) + one GitHub Actions workflow (~80 lines YAML) + three JSON
schemas + one prompt template. Fixture corpus ≤ 8 recorded CLI outputs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Every CI decision (pass/fail, post/skip) is driven by the CLI exit code plus the JSON-schema validator's boolean verdict. No downstream step inspects prose. AST lint forbids regex parsing of CLI stdout (FR-004, SC-002). |
| II. Schema-Enforced Boundaries (NN) | `--json-schema` contractually binds the CLI's output shape; `jsonschema` re-validates on the runner before pydantic parsing; `ReviewFinding`, `CLIOutputEnvelope`, `AnnotationPayload` are pydantic v2 models. Invalid payloads raise — never best-effort parsed (FR-002, FR-003). |
| III. Context Economy | Prompt template is stored once and passed by reference; no per-file prose accumulates in the workflow YAML. The review prompt itself pins stable guardrails at the top and injects the diff as dynamic suffix. |
| IV. Subagent Isolation | The CLI invocation is a one-shot subagent call: the workflow passes only the diff + prompt and consumes only the typed JSON envelope back. No conversational memory leaks between runs. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` will be run before any production code per Constitution; tasks will be generated from the Gherkin features produced by testify. Anti-pattern tests (schema-violation fixture, regex-in-mapper lint) fail closed. |
| VI. Human-in-the-Loop Escalation | Oversized PR and non-zero CLI exit surface as failed CI with a labeled reason in the job log; the human reviewer on the PR is the escalation target. No silent retry. |
| VII. Provenance & Self-Audit | `reviews/<run-id>/raw.json` is retained for 100% of runs (SC-004). Every annotation traces deterministically to one `ReviewFinding` in the uploaded payload — the audit trail is complete and offline-replayable. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function in `mapper.py`, the workflow YAML, and each schema will carry a *why* comment tied to the kata's anti-pattern defense. A kata `README.md` with objective / walkthrough / anti-pattern defense / run instructions / reflection is delivered at `/iikit-07-implement`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/013-headless-ci-review/
  plan.md              # this file
  research.md          # Phase 0 output (decisions + Tessl discovery notes)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output (JSON schemas, $id kata-013)
    review-finding.schema.json
    cli-output-envelope.schema.json
    annotation-payload.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
.github/
  workflows/
    ci-review.yml                # non-interactive `claude -p ... --output-format json --json-schema ...`
                                 # step chain: checkout → install CLI → invoke → validate → map → upload
                                 # (FR-001, FR-002, FR-003, FR-006)

katas/
  013_headless_ci_review/
    __init__.py
    review_prompt.md             # review instruction template (FR-007)
    schema/
      review_finding.schema.json # mirror of contracts/ for runtime loading
    validator.py                 # thin jsonschema wrapper used by `validate_review_output` step
    mapper.py                    # reads schema-valid dict, emits AnnotationPayloads via `gh api`
                                 # MUST NOT import `re`, call `.split`, or slice raw stdout
    models.py                    # pydantic v2: ReviewFinding, CLIOutputEnvelope, CIJob, AnnotationPayload
    annotator.py                 # thin wrapper around `gh api`/Checks API (injectable for tests)
    runner.py                    # CLI entrypoint: `python -m katas.013_headless_ci_review.runner`
    README.md                    # kata narrative (written during /iikit-07)

tests/
  katas/
    013_headless_ci_review/
      conftest.py                # fixture loader + fake `gh api` client
      features/                  # Gherkin files produced by /iikit-04-testify
        headless_ci_review.feature
      step_defs/
        test_headless_ci_review_steps.py
      unit/
        test_validator_fail_closed.py
        test_mapper_happy_path.py
        test_empty_findings.py
        test_artifact_retention.py
      lint/
        test_no_regex_parsing.py # AST check: mapper.py MUST NOT import `re`, call `.findall`/`.search`,
                                 # use `.split`, or iterate over raw stdout bytes/str (FR-004, SC-002)
      fixtures/
        valid_findings.json
        schema_violation.json
        empty_findings.json
        zero_changed_files.json
        oversized_pr.json
        cli_nonzero_exit.sh      # shim: exits 2, writes to stderr
```

**Structure Decision**: Single-project layout matching the baseline established
in Kata 001. Each kata remains a first-class package under
`katas/NNN_<slug>/`; tests mirror that under `tests/katas/NNN_<slug>/`. The
only new top-level directory is `.github/workflows/` for the CI workflow
itself — unavoidable for GitHub Actions and shared across the repo. Per-run
artifacts land under `reviews/<run-id>/` (gitignored; uploaded via
`actions/upload-artifact@v4`). This keeps the 20 katas independently buildable
and testable, matching FDD cadence.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: retries with exponential backoff on
transient CLI failures (a non-zero exit is a fail-closed event per FR-009 —
retrying would obscure the signal the kata is teaching), diff-size
pre-trimming (truncating input to fit context would violate the edge-case
contract to fail closed on oversize), and a custom annotation UI layer (the
GitHub Checks API already renders inline annotations deterministically). None
are required by the spec; adding them would directly undermine the fail-closed
stance the Constitution mandates.
