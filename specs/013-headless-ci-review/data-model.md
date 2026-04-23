# Phase 1 Data Model: Headless CI/CD Review with Claude Code CLI

All entities are pydantic v2 models at `katas/013_headless_ci_review/models.py`.
The CLI output is JSON-Schema-validated FIRST (jsonschema Draft 2020-12),
THEN parsed into these models. Any step that tries to use raw stdout directly
is a Principle II / FR-004 violation.

## ReviewFinding

One reviewer comment. Maps 1:1 to a GitHub Checks API annotation.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Stable within a run; used in annotations to de-dupe. |
| `file_path` | `str` | Path relative to repo root. |
| `line` | `int` (≥ 1) | 1-indexed line number. |
| `end_line` | `int \| None` | Optional range end. |
| `severity` | `Literal["info", "warning", "error"]` | Controls Checks annotation_level. |
| `category` | `str` | Free-form bucket for the reviewer prompt (e.g. "security", "readability"). |
| `message` | `str` | Human-readable finding. Rendered as annotation message. |
| `suggested_fix` | `str \| None` | Optional. Appears in annotation's `raw_details`. |

**Invariants**
- `line ≥ 1`; `end_line ≥ line` when present.
- The `id` is deterministic per `(file_path, line, category)` so re-runs on the
  same diff don't spam the PR with duplicate comments.

## CLIOutputEnvelope

The top-level object the Claude Code CLI emits. Its JSON Schema is what we
pass via `--json-schema` so the SDK refuses to emit anything else.

| Field | Type | Notes |
|-------|------|-------|
| `schema_version` | `str` | Declared constant, e.g. `"1.0"`. |
| `findings` | `list[ReviewFinding]` | May be empty (zero-findings run is valid). |
| `summary` | `str` | Short overall note. |
| `metadata` | `dict` | Free-form audit metadata (run id, model id, prompt hash). |

**Validation pipeline**
1. `jsonschema.validate(raw_stdout_json, cli_output_envelope_schema)` — step
   `validate_review_output` in the workflow.
2. `CLIOutputEnvelope.model_validate(raw_stdout_json)` — second gate catches
   invariants the schema can't express.
3. Mapper consumes the validated model only.

## AnnotationPayload

What the mapper posts to GitHub's Checks API per finding.

| Field | Type | Notes |
|-------|------|-------|
| `path` | `str` | Same as `ReviewFinding.file_path`. |
| `start_line` | `int` | Mapped from `line`. |
| `end_line` | `int` | Mapped from `end_line ?? line`. |
| `annotation_level` | `Literal["notice", "warning", "failure"]` | Mapping: info→notice, warning→warning, error→failure. |
| `message` | `str` | `ReviewFinding.message`. |
| `title` | `str` | `f"[{category}] {id}"`. |
| `raw_details` | `str \| None` | `suggested_fix` if present. |

## CIJob (audit entity, not serialized back to the CLI)

| Field | Type | Notes |
|-------|------|-------|
| `run_id` | `str` | GitHub Actions run id. |
| `pr_number` | `int` | Pull request number. |
| `status` | `Literal["success", "schema_failure", "cli_failure", "mapping_failure"]` | Terminal status; `schema_failure` and `cli_failure` fail the job closed. |
| `artifacts_uploaded` | `list[str]` | Paths retained (`raw.json`, `stderr.log`, etc.). |
| `findings_posted` | `int` | 0 when the envelope is empty; NOT a failure. |

## Why this shape

- `CLIOutputEnvelope` is the sole source of truth. No field on downstream
  models is constructed from regex/split on raw stdout — FR-004 / SC-002
  operationalized as a design rule.
- `ReviewFinding.id` deterministic → `AnnotationPayload` idempotent across
  retries.
- `CIJob.status` surfaces each failure mode distinctly so the workflow badge
  communicates what actually broke.
