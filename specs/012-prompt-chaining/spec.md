# Feature Specification: Multi-Pass Prompt Chaining

**Feature Branch**: `012-prompt-chaining`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 12 — Avoid model cognitive saturation when auditing many files by decomposing the macro task into sequential prompt passes (per-file local analysis, then integration-only pass)."

## User Stories *(mandatory)*

### User Story 1 - Chained Audit of a Multi-File Pull Request (Priority: P1)

A practitioner feeds a multi-file pull request (e.g. 15 files) into the workflow. The chain first produces one focused per-file report per input, then an integration-only report that evaluates inter-module coherence across the accumulated reports. The two output classes are kept distinct and traceable back to the stage that produced them.

**Why this priority**: This is the core value of the kata — it is the MVP that proves decomposition avoids cognitive saturation and produces deeper findings than a single monolithic prompt. Without this story, no other user story makes sense.

**Independent Test**: Can be fully tested by submitting a corpus of N files, observing that the artifact set contains exactly N per-file reports plus one integration report, and that the integration report references inter-module relationships rather than restating per-file issues.

**Acceptance Scenarios**:

1. **Given** a macro task consisting of 15 files to audit, **When** the practitioner runs the chain, **Then** the workflow emits 15 per-file reports and 1 integration report as distinct artifacts.
2. **Given** the per-file pass has completed, **When** the integration pass runs, **Then** its prompt contains the accumulated per-file reports and explicit instruction to evaluate ONLY inter-module incoherences.
3. **Given** the final integration report, **When** it is inspected, **Then** it contains no re-analysis of single-file local issues already covered in per-file reports.

---

### User Story 2 - Baseline Comparison Against the Monolithic Anti-Pattern (Priority: P2)

A practitioner runs a baseline where all files are crammed into one monolithic prompt asking for both local and integration analysis at the same time. They then compare the baseline against the chained run on the same corpus and observe missed findings, shallow findings, or dilution in the baseline output.

**Why this priority**: This story empirically justifies the kata's existence by demonstrating the anti-pattern's cost. It is secondary because P1 already delivers value independently; this story adds the evidence that the chain is superior.

**Independent Test**: Can be tested by running both modes on an identical corpus and producing a side-by-side delta report showing finding counts, depth, and categorization per mode.

**Acceptance Scenarios**:

1. **Given** the same corpus used in US1, **When** the practitioner runs the baseline monolithic prompt, **Then** the output is captured as a single artifact for comparison.
2. **Given** both the chained and baseline outputs, **When** the practitioner performs a delta comparison, **Then** the chain exhibits at least the declared coverage delta of findings over the baseline.

---

### User Story 3 - Extending the Chain With an Additional Stage (Priority: P3)

A practitioner adds a new stage (e.g. a security-focused scan pass) to the chain without modifying any earlier stage's prompt, payload contract, or output. The new stage consumes existing intermediate payloads and emits its own report.

**Why this priority**: Demonstrates that the chain is composable and forward-extensible. This is valuable long-term but not required for the MVP chain to function.

**Independent Test**: Can be tested by adding one new stage definition, rerunning the chain, and verifying that no prior stage's file, prompt, or artifact was modified.

**Acceptance Scenarios**:

1. **Given** an existing chain with per-file and integration stages, **When** the practitioner declares a new security stage downstream, **Then** the chain executes the new stage using existing intermediate payloads.
2. **Given** the extension is complete, **When** the diff of earlier stage definitions is inspected, **Then** zero changes are observed in those earlier stage files.

---

### Edge Cases

- What happens when the corpus contains very few files (e.g. 1–2), making chain overhead arguably larger than the saturation it prevents?
- How does the system handle a per-file report whose size exceeds the downstream integration stage's context budget?
- What happens when one file fails to analyze (timeout, parse error, tool failure) while the rest succeed?
- How are conflicting findings across per-file reports surfaced during the integration pass without silently reconciling them?
- What happens when the intermediate payload is structurally malformed (missing required fields, corrupted accumulation)?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST decompose any macro audit task into a set of explicitly declared stages, each with a named responsibility.
- **FR-002**: The system MUST persist intermediate payloads between stages so that downstream stages consume the accumulated outputs of upstream stages rather than re-reading the raw corpus.
- **FR-003**: The system MUST restrict each stage's prompt to its declared responsibility (e.g. per-file pass analyzes local issues only; integration pass evaluates inter-module incoherences only).
- **FR-004**: The system MUST fail loud (surface an explicit error and halt the chain) if an intermediate payload is malformed, missing required fields, or truncated.
- **FR-005**: The system MUST allow the chain to be extended by adding new stages downstream without requiring modification of existing stage definitions, prompts, or payload contracts.
- **FR-006**: The system MUST emit per-file reports and the integration report as distinct, separately addressable artifacts.
- **FR-007**: The system MUST record which stage produced each artifact so findings are traceable to their originating pass.
- **FR-008**: The system MUST surface per-file analysis failures rather than silently skipping or absorbing them into a partial integration report.

### Key Entities

- **Macro Task**: The overall audit objective (e.g. "audit this 15-file pull request"). Holds the input corpus reference and the declared chain of stages.
- **Stage**: A single pass in the chain with a declared responsibility, a prompt template scoped to that responsibility, and a defined input/output payload contract.
- **Intermediate Payload**: The structured accumulation of upstream stage outputs that is handed to the next stage. Schema-validated at stage boundaries.
- **Final Report**: The integration-pass output that evaluates inter-module coherence across the accumulated per-file reports, distinct from per-file artifacts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Finding coverage produced by the chained run is greater than or equal to the baseline (monolithic prompt) run by at least the declared delta on the same corpus.
- **SC-002**: Each stage's prompt stays under its declared size budget (tokens or characters) across all runs in the evaluation set.
- **SC-003**: Zero silent swallowing of failed stages — 100% of per-file analysis failures surface as explicit errors in the chain's output.
- **SC-004**: Adding a new stage to the chain requires zero changes to existing stage definitions, prompts, or payload contracts (verified by diff).
