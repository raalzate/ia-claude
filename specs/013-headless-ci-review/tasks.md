# Tasks: Headless CI/CD Review with Claude Code CLI

**Input**: Design documents from `/specs/013-headless-ci-review/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/*.schema.json, tests/features/*.feature

## Format: `- [ ] T### [P?] [USn?] Description with file path`
- [P] parallel, [USn] story only
- Traceability: `[TS-001, TS-002]`, never ranges

---

## Phase 1: Setup

- [ ] T001 Create kata package skeleton `katas/013_headless_ci_review/__init__.py` with module docstring stating objective (deterministic headless reviewer, Principle I+II+VIII) and listing public entry points (`runner`, `validator`, `mapper`).
- [ ] T002 [P] Create test package skeleton `tests/katas/013_headless_ci_review/__init__.py` and `tests/katas/013_headless_ci_review/conftest.py` exposing fixture loaders for `valid_findings.json`, `schema_violation.json`, `empty_findings.json`, `zero_changed_files.json`, `oversized_pr.json`, plus a fake `gh api` client (records calls; never hits the network).
- [ ] T003 [P] Add dev dependencies to repo tooling (`pyproject.toml` or equivalent): `pydantic>=2`, `jsonschema>=4.18` (Draft 2020-12), `pytest`, `pytest-bdd`. Add `re` to AST lint deny-list configuration note.
- [ ] T004 [P] Create fixture directory `tests/katas/013_headless_ci_review/fixtures/` and populate: `valid_findings.json` (two findings, severities info+error), `schema_violation.json` (missing `findings` field), `empty_findings.json` (schema-valid, `findings: []`), `zero_changed_files.json` (empty envelope variant), `oversized_pr.json` (sentinel payload), and `cli_nonzero_exit.sh` (shebang shim: writes "ctx too large" to stderr, exits 2).
- [ ] T005 [P] Mirror JSON schemas from `specs/013-headless-ci-review/contracts/` into runtime location `katas/013_headless_ci_review/schema/{review_finding,cli_output_envelope,annotation_payload}.schema.json` so the validator loads them without crossing the `specs/` boundary.

---

## Phase 2: Foundational (blocking prerequisites for all user stories)

- [ ] T006 Implement pydantic v2 models in `katas/013_headless_ci_review/models.py`: `ReviewFinding`, `CLIOutputEnvelope`, `AnnotationPayload`, `CIJob`. Include field docstrings citing data-model.md, invariants (`line >= 1`, `end_line >= line`), and `CIJob.status` Literal `["success","schema_failure","cli_failure","mapping_failure"]`. Why-comment: "single source of truth for downstream; never constructed from raw stdout (FR-004, SC-002)".
- [ ] T007 Implement schema validator in `katas/013_headless_ci_review/validator.py`: wraps `jsonschema` Draft 2020-12 validation against `cli_output_envelope.schema.json`. Raises typed `SchemaViolationError` on drift. Module docstring: why this runs BEFORE pydantic parsing (FR-003, FR-004). Why-comment on the raise path: "fail closed, never fall back to regex".
- [ ] T008 Implement annotator wrapper in `katas/013_headless_ci_review/annotator.py`: thin class calling `gh api repos/:owner/:repo/check-runs`; constructor-injectable transport for tests; refuses any input that is not an `AnnotationPayload` instance. Why-comment: "only typed payloads cross this boundary".
- [ ] T009 Implement mapper in `katas/013_headless_ci_review/mapper.py`: consumes validated `CLIOutputEnvelope`, emits `list[AnnotationPayload]`, deterministic severity→annotation_level map (info→notice, warning→warning, error→failure), deterministic `title = f"[{category}] {id}"`. MUST NOT import `re`, call `.split`, or touch raw stdout. Module docstring: "anti-pattern defense — regex parsing is the kata's forbidden path (FR-004, SC-002)". Why-comment on each branch.
- [ ] T010 Implement CLI runner entrypoint in `katas/013_headless_ci_review/runner.py` executed as `python -m katas.013_headless_ci_review.runner`: orchestrates read-stdin → validate → pydantic-parse → map → annotator.post; exit codes documented inline (`0` success/empty, `2` schema_failure, `3` cli_failure, `4` mapping_failure). Module docstring pins the headless invocation contract (exit codes) for README cross-reference.
- [ ] T011 Author review prompt template `katas/013_headless_ci_review/review_prompt.md`: stable guardrails at top (output MUST validate against declared JSON schema; zero prose outside envelope); dynamic diff suffix marker; why-comment: "stored outside the workflow YAML so prompt edits never touch CI glue (FR-007)".

---

## Phase 3: User Story 1 — Automated inline review on every pull request (P1)

**Goal**: A non-interactive CLI call on every PR produces inline annotations without human intervention.

**Independent test**: Open a throwaway PR; CI workflow runs; at least one inline annotation posts; no manual step.

- [ ] T012 [US1] Create GitHub Actions workflow `.github/workflows/ci-review.yml` with `on: pull_request`, job `ci-review` (ubuntu-latest) and step chain: checkout → install `claude` CLI → invoke `claude -p "$(cat katas/013_headless_ci_review/review_prompt.md)" --output-format json --json-schema katas/013_headless_ci_review/schema/cli_output_envelope.schema.json > reviews/${{ github.run_id }}/raw.json 2> reviews/${{ github.run_id }}/stderr.log` → `validate_review_output` step → `python -m katas.013_headless_ci_review.runner` → `actions/upload-artifact@v4` with `if: always()`. Why-comments on each step citing FR-001, FR-002, FR-006.
- [ ] T013 [P] [US1] Step-def: `--print` flag enforcement in `tests/katas/013_headless_ci_review/step_defs/test_headless_ci_review_steps.py` binding `automated_inline_review.feature` scenario "CLI runs non-interactively with the --print flag". Asserts the workflow invocation string contains `-p` / `--print` and no TTY. Cites [TS-001].
- [ ] T014 [P] [US1] Step-def: structured-output declaration binding scenario "CLI invocation declares structured output contract". Asserts workflow passes `--output-format json` AND `--json-schema <path>`. Cites [TS-002].
- [ ] T015 [US1] Step-def: validated findings become inline annotations binding scenario "Validated findings become inline annotations on the PR diff". Uses `valid_findings.json` fixture + fake `gh api` client; asserts one annotation per finding with matching `path` and `start_line`. Cites [TS-003].
- [ ] T016 [US1] Step-def: severity→annotation_level outline binding scenario "Severity maps deterministically to annotation_level". Parameterized over info→notice, warning→warning, error→failure. Cites [TS-004].
- [ ] T017 [P] [US1] Unit test `tests/katas/013_headless_ci_review/unit/test_mapper_happy_path.py`: pure mapper call on `valid_findings.json` yields expected `AnnotationPayload` list (titles `"[security] f-1"` etc.); deterministic ordering.

**Checkpoint**: US1 standalone — push a PR, see annotations.

---

## Phase 4: User Story 2 — Schema-enforced output, fail closed on drift (P2)

**Goal**: Any drift from the declared JSON schema fails the job; no regex fallback; raw artifacts retained.

**Independent test**: Stub a schema-violating CLI response; CI step fails with schema-violation error; no annotations posted.

- [ ] T018 [US2] Step-def: schema-valid envelope passes binding scenario "Schema-valid envelope passes validation and is handed to the mapper". Uses `valid_findings.json`; asserts validator exits 0 and mapper is called. Cites [TS-005].
- [ ] T019 [US2] Step-def: schema-invalid envelope fails closed binding scenario "Schema-invalid envelope fails the job closed". Uses `schema_violation.json`; asserts non-zero exit, zero annotator calls, and that the `validator.py` code path raises before reaching the mapper. Cites [TS-006].
- [ ] T020 [US2] AST lint `tests/katas/013_headless_ci_review/lint/test_no_regex_parsing.py` binding scenario "Mapper source code contains no free-form text parsing": walks `ast.parse(mapper.py)`; fails on `import re`, `re.findall`, `re.search`, `.split(` calls, and any direct read of `sys.stdin` / raw stdout bytes. Cites [TS-007].
- [ ] T021 [P] [US2] Step-def: CLI non-zero exit fails closed binding scenario "CLI exits non-zero and the job fails closed". Drives `cli_nonzero_exit.sh` through runner; asserts exit code 3, stderr retained, no annotator calls. Cites [TS-008].
- [ ] T022 [P] [US2] Step-def: oversized PR fails closed binding scenario "Oversized PR input fails closed with a labeled reason". Feeds `oversized_pr.json`; asserts job fails with `oversized-context` reason string and zero annotations. Cites [TS-009].
- [ ] T023 [P] [US2] Step-def: zero-changed-files branch binding scenario "Zero-changed-files PR produces empty findings and posts nothing". Feeds `zero_changed_files.json` → schema-valid empty envelope; asserts exit 0, zero annotator calls. Cites [TS-010].
- [ ] T024 [US2] Step-def: raw-artifact retention outline binding scenario "Raw CLI response is retained regardless of outcome". Parameterized across `success`, `schema_failure`, `cli_failure`, `mapping_failure`; asserts the workflow's `upload-artifact` step runs under `if: always()` and targets both `reviews/<run-id>/raw.json` and `reviews/<run-id>/stderr.log`. Cites [TS-011].
- [ ] T025 [P] [US2] Unit test `tests/katas/013_headless_ci_review/unit/test_validator_fail_closed.py`: validator raises `SchemaViolationError` on missing-field, wrong-type, and extra-prose payloads; never swallows.
- [ ] T026 [P] [US2] Unit test `tests/katas/013_headless_ci_review/unit/test_empty_findings.py`: empty-findings envelope produces zero annotator calls and exit 0 (FR-008).
- [ ] T027 [P] [US2] Unit test `tests/katas/013_headless_ci_review/unit/test_artifact_retention.py`: runner records uploaded artifact paths on every terminal status (`success`, `schema_failure`, `cli_failure`, `mapping_failure`).

### Contract scenarios (bound to `schema_contracts.feature`)

- [ ] T028 [P] [US2] Step-def: CLIOutputEnvelope rejects missing `findings` binding scenario "CLIOutputEnvelope rejects payloads missing required fields". Cites [TS-015].
- [ ] T029 [P] [US2] Step-def: ReviewFinding field invariants outline binding scenario "ReviewFinding enforces field-level invariants" across `line=0`, `line=-1`, `severity=critical`, `severity=INFO`, empty `id`, empty `message`. Cites [TS-016].
- [ ] T030 [P] [US2] Step-def: ReviewFinding accepts well-formed payload binding scenario "ReviewFinding accepts a well-formed payload". Cites [TS-017].
- [ ] T031 [P] [US2] Step-def: AnnotationPayload rejects `annotation_level=error` binding scenario "AnnotationPayload enforces the Checks API annotation_level enum". Cites [TS-018].
- [ ] T032 [P] [US2] Step-def: AnnotationPayload accepts well-formed payload binding scenario "AnnotationPayload accepts a well-formed payload". Cites [TS-019].

**Checkpoint**: US1 + US2 standalone — pipeline trustworthy; schema drift fails closed; contracts locked.

---

## Phase 5: User Story 3 — Swap the review prompt without touching CI glue (P3)

**Goal**: Editing only `review_prompt.md` changes the next run's behavior; no workflow or mapper change required.

**Independent test**: Replace prompt body; re-run; new objective reflected; no diff to `.github/workflows/ci-review.yml` or `mapper.py`.

- [ ] T033 [US3] Step-def: prompt lives outside workflow binding scenario "Prompt template lives outside the workflow definition". Parses `.github/workflows/ci-review.yml`; asserts the prompt is referenced by file path and the YAML contains no inlined prompt body. Cites [TS-012].
- [ ] T034 [US3] Step-def: edit-only-prompt changes next run binding scenario "Editing only the prompt changes the next run's behavior". Uses a git-diff probe: mutate `review_prompt.md`, run the CLI stub, assert workflow YAML and `mapper.py` hashes are unchanged, assert the new prompt bytes were passed to the CLI stub. Cites [TS-013].
- [ ] T035 [US3] Step-def: new prompt still schema-valid binding scenario "New prompt still produces schema-valid output". Runs the validator on the new-prompt CLI stub output and asserts exit 0. Cites [TS-014].

**Checkpoint**: All three stories deliverable independently.

---

## Final Phase: Polish & Documentation (Principle VIII)

- [ ] T036 Author `katas/013_headless_ci_review/notebook.ipynb` — single Principle VIII deliverable, replaces the README and folds in every previously requested README sub-section. Notebook is the kata's primary teaching artifact for Claude architecture certification prep; design and impl stay simple. Ordered cells (markdown unless noted):
  1. **Objective & anti-pattern** — kata goal in plain language; the anti-pattern it structurally defends against.
  2. **Concepts (Claude architecture certification)** — headless mode (`-p`), `--output-format json`, `--json-schema` schema-bound output, GitHub Checks API integration, deterministic severity → annotation_level mapping, AST lint forbidding `re` / `.split` / raw-stdout in mapper, exit-code semantics, prompt-glue decoupling — each with a one-line definition tied to the certification syllabus.
  3. **Architecture walkthrough** — components (GitHub Actions → `claude -p --output-format json --json-schema` → `validator` → pydantic parse → `mapper` → `annotator` (Checks API) → artifact upload) and the data flow as an ASCII or mermaid block diagram.
  4. **Patterns** — schema-bound headless output, validate-before-parse, regex-as-forbidden-fallback, prompt-stored-outside-CI-glue — each with the trade-off it solves.
  5. **Principles & recommendations** — Constitution principles enforced (I Determinism, II Schema-First, V Test-First, VIII Documentation) cross-referenced to Anthropic engineering recommendations; practitioner-facing checklist for applying these on a real project.
  6. **Contract** — headless invocation contract table (`-p` → no TTY; `--output-format json` → parseable; `--json-schema` → schema-bound); exit codes table (`0` success or schema-valid empty; `2` schema_failure; `3` cli_failure; `4` mapping_failure); the six README sections (Objective, Headless CLI architecture, CI integration with `.github/workflows/ci-review.yml`, Anti-pattern defense, Run, Reflection) all become notebook cells (folded in from former README sub-sections).
  7. **Run** — executable cells reproducing the fixture run; a final commented cell for the LIVE_API=1 path.
  8. **Result** — captured outputs / metrics / event-log excerpts from the run with explanations.
  9. **Reflection (Principle VIII)** — answers to the prompts in quickstart.md.
- [ ] T037 [P] Add module-level docstrings to `validator.py`, `mapper.py`, `annotator.py`, `runner.py`, `models.py` that each cite the FR(s) they implement and the anti-pattern they defend against.
- [ ] T038 [P] Add why-comments to every non-trivial branch in `mapper.py`, `validator.py`, and the workflow YAML keyed to anti-pattern defense (regex avoidance, fail-closed on drift, 100% artifact retention).
- [ ] T039 [P] Verify quickstart end-to-end: execute each command in `specs/013-headless-ci-review/quickstart.md` (install, local dry-run, `pytest tests/katas/013_headless_ci_review -v`); update quickstart if any command diverges; add a GitHub Actions workflow example block mirroring `.github/workflows/ci-review.yml` to the quickstart.
- [ ] T040 [P] Cross-link a final markdown cell of `notebook.ipynb`, `quickstart.md`, `spec.md`, and `plan.md` (relative links) so a practitioner entering at any doc can reach the others.
- [ ] T041 Final traceability audit: confirm every `@TS-001`..`@TS-019` tag in `tests/features/*.feature` has a matching step-def task above (TS-001→T013, TS-002→T014, TS-003→T015, TS-004→T016, TS-005→T018, TS-006→T019, TS-007→T020, TS-008→T021, TS-009→T022, TS-010→T023, TS-011→T024, TS-012→T033, TS-013→T034, TS-014→T035, TS-015→T028, TS-016→T029, TS-017→T030, TS-018→T031, TS-019→T032); confirm every FR-00N and SC-00N appears in at least one task citation; fix any gap by adding a task rather than weakening a scenario.
- [ ] T042 Regenerate dashboard: run `bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/generate-dashboard-safe.sh` and confirm `.specify/dashboard.html` reflects Kata 013 task counts.
