# Feature Specification: Few-Shot Calibration for Edge Cases

**Feature Branch**: `014-few-shot-calibration`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 14 — Tune the model's attention weight toward highly subjective or unconventional output formats by providing 2–4 representative input/output examples in the prompt, escaping generic zero-shot defaults."

## User Stories *(mandatory)*

### User Story 1 - Zero-Shot Baseline vs. Calibrated Few-Shot on an Edge-Case Corpus (Priority: P1)

A practitioner curates a corpus of edge-case inputs for a highly subjective task (for example, interpreting informal culinary measures such as "a pinch of salt"). They first run the task on the corpus in zero-shot mode and record the failure/inconsistency rate. They then add 2–4 explicit structured input/output example pairs to the prompt and re-run the same corpus. They observe and record a significant improvement in format conformance and consistency.

**Why this priority**: This is the core loop of the kata — without a measured before/after on the same corpus, "calibration" is an anecdote rather than an engineering technique. It is also the smallest slice that delivers standalone value: one corpus, one prompt change, one measured improvement.

**Independent Test**: Can be fully tested by running the edge-case corpus once zero-shot, recording the inconsistency rate, running it again with a calibrated example set, and confirming the recorded delta meets the declared threshold.

**Acceptance Scenarios**:

1. **Given** an edge-case corpus and a zero-shot prompt, **When** the practitioner executes the run, **Then** the system records a baseline failure/inconsistency rate for the corpus.
2. **Given** the same corpus and a prompt augmented with 2–4 structured input/output examples, **When** the practitioner executes the run, **Then** the system records a post-calibration rate and the delta against the baseline.
3. **Given** a completed calibrated run, **When** the practitioner inspects the logs, **Then** the active example set is identifiable per run.

---

### User Story 2 - Demonstrate the Anti-Pattern and Measure the Delta (Priority: P2)

A practitioner deliberately demonstrates the documented anti-pattern — relying on zero-shot prompting for a highly subjective or format-sensitive task and then attempting to fix inconsistency turn after turn via prompt tweaks — on the same inputs used for the few-shot run. The measured delta between the anti-pattern approach and the calibrated few-shot approach is recorded as evidence.

**Why this priority**: The kata's educational payload depends on making the anti-pattern concrete and measurable. Without this story, practitioners may treat few-shot calibration as optional polish rather than the correct default for subjective/format-sensitive tasks.

**Independent Test**: Can be fully tested by executing both approaches against the same identical input set and verifying that a single artifact records both rates and the computed delta.

**Acceptance Scenarios**:

1. **Given** an identical input set used for both approaches, **When** zero-shot and few-shot runs complete, **Then** both results are recorded side by side with the computed delta.
2. **Given** a zero-shot run attempting to fix format issues via successive prompt tweaks, **When** the practitioner inspects the outcome, **Then** the inconsistency pattern is documented as the defended anti-pattern.

---

### User Story 3 - Rotate the Example Set and Observe Sensitivity (Priority: P3)

A practitioner swaps the active example set for an alternative set of the same size (still 2–4 pairs) covering different edge cases or of different quality. They re-run the corpus and observe how output quality changes, producing a sensitivity record that shows example quality — not merely example count — is the driver.

**Why this priority**: This story deepens understanding but is not required to demonstrate the core calibration benefit. It becomes valuable after P1 and P2 are in place.

**Independent Test**: Can be fully tested by running the corpus with at least two distinct example sets, confirming each run logs which set was active, and comparing the resulting rates.

**Acceptance Scenarios**:

1. **Given** two or more distinct example sets of size 2–4, **When** the practitioner runs the corpus with each, **Then** each run records the active example set identifier and its measured rate.
2. **Given** two completed runs with different example sets, **When** the practitioner compares the results, **Then** the sensitivity to example quality is documented.

---

### Edge Cases

- What happens when the example set contains contradictory input/output pairs (for example, two examples mapping similar inputs to incompatible outputs)?
- What happens when an example pair appears to leak memorized training data (a verbatim canonical input/output) rather than representing the task's edge-case distribution?
- What happens when a corpus input is very different from any provided example (out-of-distribution relative to the calibration set)?
- What happens when individual examples are so long that they dominate the prompt context budget or push relevant content out of scope?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST include 2–4 input/output example pairs in the prompt when measured zero-shot performance on the edge-case corpus is below the declared threshold.
- **FR-002**: System MUST validate that the active example set covers representative edge cases for the task before that set is used in a calibrated run.
- **FR-003**: System MUST log which example set was active for each run, such that any recorded result can be traced to its calibration inputs.
- **FR-004**: System MUST measure and record the zero-shot vs. few-shot delta on the same corpus, producing a single comparable metric per corpus.
- **FR-005**: System MUST treat a contradictory example set as an error condition and refuse to run it silently; contradictions MUST surface as a validation failure rather than degraded output.
- **FR-006**: System MUST reject or flag example sets whose size falls outside the 2–4 pair range so that calibration stays within the kata's defined envelope.
- **FR-007**: System MUST defend against the documented anti-pattern by requiring explicit acknowledgement when a subjective or format-sensitive task is executed in zero-shot mode.

### Key Entities

- **Edge-Case Task**: A task whose correct output format is subjective, unconventional, or otherwise prone to zero-shot inconsistency (e.g., interpreting informal measures like "a pinch of salt" into a structured quantity).
- **Example Pair**: A single structured input/output record demonstrating the desired mapping for one edge case (e.g., `Input: "A pinch of salt" → Output: {"amount": "~1g", "precision": "approximate"}`).
- **Example Set**: A named, versioned collection of 2–4 Example Pairs used together to calibrate one run; carries an identifier, a coverage description, and a contradiction-check status.
- **Performance Delta**: The measured difference between zero-shot and few-shot runs on the same edge-case corpus, capturing baseline rate, post-calibration rate, and the computed improvement.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Few-shot calibration reduces the inconsistency rate on the edge-case corpus by at least a declared X% compared to the zero-shot baseline on the same inputs.
- **SC-002**: 100% of calibrated runs produce schema-valid output for the declared edge-case task format.
- **SC-003**: 0 silently-contradictory example sets are accepted — every contradictory set surfaces as a validation failure before the run executes.
- **SC-004**: The active example set is logged and retrievable for 100% of runs (zero-shot and few-shot alike), so any result can be traced back to its calibration inputs.
