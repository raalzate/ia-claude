# Feature Specification: Headless CI/CD Review with Claude Code CLI

**Feature Branch**: `013-headless-ci-review`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Integrate a deterministic agentic reviewer directly into automated CI/CD pipelines using the Claude Code CLI, invoked non-interactively with structured JSON output, so that every pull request receives schema-validated inline annotations without free-form regex parsing."

## Clarifications

### 2026-04-24 (phase-06 analyze)

- **SC-003 numeric gate**: default annotation-landing gate is `≥ 95%` — at least 95% of CI runs whose reviewer output is schema-valid AND has a non-empty findings set post at least one inline annotation on the pull request. This is an automated, checkable gate at kata run time.
- **Oversized-context detection (FR-009)**: detection is a pre-CLI size check. The runner estimates input token count using the same tokenizer family used by the CLI (e.g. `tiktoken` with the configured model encoding), compares against the configurable constant `MAX_INPUT_TOKENS` (default `180_000`), and fails the job with a labeled `oversized-context` reason when the estimate exceeds the constant. This is authoritative; CLI-exit-signal detection is a secondary fallback only.

## User Stories *(mandatory)*

### User Story 1 - Automated inline review on every pull request (Priority: P1)

A practitioner opens a pull request against the workshop repository. A CI job runs the Claude Code CLI in headless mode, asks it to analyze the changed files, receives a structured response, and automatically posts inline annotations on the PR without any human kicking off the reviewer by hand.

**Why this priority**: This is the minimum viable outcome that satisfies the Development Workflow section of `CONSTITUTION.md` v1.2.0 (automated deterministic reviewer on each PR). Without it, the kata has no demonstrable value — an agentic reviewer that is not wired into CI is just a local script.

**Independent Test**: Open a throwaway pull request with at least one changed file. The CI workflow triggers, the headless reviewer runs, and at least one inline annotation appears on the PR diff within the CI run, with no manual step between "push" and "annotation visible".

**Acceptance Scenarios**:

1. **Given** a pull request is opened with one or more changed files, **When** the CI workflow runs, **Then** the Claude Code CLI is invoked non-interactively and the job completes without any interactive prompt.
2. **Given** the reviewer produces a valid structured response, **When** the CI step that maps findings to the repository runs, **Then** each finding appears as an inline annotation attached to the relevant file and line on the pull request.

---

### User Story 2 - Schema-enforced output, fail-closed on drift (Priority: P2)

A practitioner asserts that the review output always conforms to the declared JSON schema. If the model returns anything that does not validate — missing fields, wrong types, extra free-form prose, truncated JSON — the CI step fails the job instead of silently degrading into regex parsing.

**Why this priority**: This is the direct defense against the kata's documented anti-pattern ("letting the agent output free-form prose that the CI script then has to parse with regex") and enforces Principle II (Schema-Enforced Boundaries) of `CONSTITUTION.md`. It is P2 rather than P1 because the pipeline can produce annotations (P1) before it is hardened against drift, but it cannot be considered trustworthy until drift fails closed.

**Independent Test**: Inject a stub reviewer response that violates the schema (e.g., remove a required field). The CI step must fail with a clear schema-violation error, and no annotations must be posted for that run.

**Acceptance Scenarios**:

1. **Given** the reviewer response validates against the declared JSON schema, **When** the CI step validates output, **Then** the step passes and hands the findings to the annotation mapper.
2. **Given** the reviewer response does not validate against the declared JSON schema, **When** the CI step validates output, **Then** the step fails the job and no annotations are posted.

---

### User Story 3 - Swap the review prompt without touching CI glue (Priority: P3)

A practitioner changes the review prompt template (e.g., swaps "analyze for vulnerabilities" for "analyze for performance regressions") and redeploys. The CI glue code — job definition, schema validation, annotation mapping — does not need to change for the new prompt to take effect.

**Why this priority**: This is a durability and maintainability concern, not a correctness concern. The kata is useful even without this separation, but workshops iterate on prompts frequently and binding the prompt to the CI glue would create churn. Deferring to P3 lets P1 and P2 land first.

**Independent Test**: Replace the prompt template file (or prompt input) with a new review objective that conforms to the same output schema. Re-run the CI job on an unchanged PR. The new prompt is used, annotations reflect the new objective, and no CI workflow file or annotation-mapping script was modified in the same change.

**Acceptance Scenarios**:

1. **Given** the prompt template is stored separately from the CI workflow definition, **When** a practitioner edits only the prompt template, **Then** the next CI run uses the new prompt without any change to the workflow or mapping code.
2. **Given** a new prompt is deployed, **When** the reviewer runs, **Then** its output still validates against the same declared JSON schema.

---

### Edge Cases

- **CLI exits non-zero**: The Claude Code CLI exits with a non-zero status (transport error, auth failure, rate limit). The CI step MUST surface the exit code, retain stderr in the job log, and fail closed without attempting to post partial annotations.
- **Schema validation fails**: The CLI exits zero but the emitted payload does not validate against the declared JSON schema. The CI step MUST fail the job, log the offending payload, and MUST NOT fall back to regex or heuristic parsing.
- **PR has zero changed files**: The PR contains no reviewable changes (e.g., only renames or only metadata). The job MUST complete successfully, emit a schema-valid empty findings set, and post no annotations.
- **Very large PR exceeds context**: The set of changed files exceeds the model's usable context. The job MUST detect the condition (either up front or from a CLI signal), fail closed with a clear reason, and MUST NOT silently truncate input or emit unvalidated output.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST invoke the Claude Code CLI non-interactively (using the `--print` / `-p` flag) so that no TTY or human input is required inside the CI job.
- **FR-002**: System MUST request structured output using `--output-format json` together with a declared `--json-schema` so the reviewer is contractually bound to return a single valid object.
- **FR-003**: System MUST validate every reviewer response against the declared JSON schema before any downstream step consumes it.
- **FR-004**: System MUST fail the CI step when the response does not validate against the schema, and MUST NOT fall back to regex or free-form text parsing.
- **FR-005**: System MUST map each validated finding to an inline annotation on the pull request, attached to the file and line indicated in the structured finding.
- **FR-006**: System MUST log the full raw reviewer response (stdout and stderr) as a retained CI artifact for audit, regardless of whether the run succeeded or failed.
- **FR-007**: System MUST keep the review prompt template decoupled from the CI workflow definition, so the prompt can be changed without editing the workflow or the annotation-mapping code.
- **FR-008**: System MUST handle a zero-changed-files PR by producing a schema-valid empty findings set and posting no annotations, rather than failing or emitting free-form prose.
- **FR-009**: System MUST fail closed (non-zero CI status, no annotations posted) whenever the CLI exits non-zero or the input exceeds the usable context window.

### Key Entities

- **PR Under Review**: The pull request that triggered the CI job. Identified by repository, PR number, head commit, and the set of changed files and line ranges that define the review surface.
- **Review Prompt Template**: The instruction text supplied to the Claude Code CLI (e.g., "Analyze this pull request for vulnerabilities"). Versioned and stored separately from the CI workflow so it can be edited independently.
- **Review Finding**: A single item the reviewer returned. Has at minimum a file path, a line or line range, a severity, and a message. Its shape is fixed by the declared JSON schema.
- **CI Job**: The automated workflow run (e.g., on GitHub Actions) that invokes the CLI, validates output, and posts annotations. Has an exit status, a retained raw-response artifact, and a pass/fail gate tied to schema validation.
- **Annotation**: The inline comment rendered on the pull request diff. Derived deterministically from a Review Finding; never synthesized from free-form text.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of CI runs either produce schema-valid reviewer output or fail closed; zero runs post annotations derived from unvalidated output.
- **SC-002**: 0 instances of free-form regex parsing exist in the CI glue code, verified by review of the mapping script against the declared schema as the sole input contract.
- **SC-003**: Findings land as inline annotations on the pull request in ≥ 95% of runs whose reviewer output is schema-valid and has a non-empty findings set (default numeric gate; see Clarifications).
- **SC-004**: The raw reviewer response is retained as a CI artifact for 100% of runs, including runs that failed schema validation or exited non-zero.
