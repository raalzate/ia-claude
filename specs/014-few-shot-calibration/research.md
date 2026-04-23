# Phase 0 Research: Few-Shot Calibration for Edge Cases

## Decisions

### D-001 — Use the official `anthropic` Python SDK for both arms

- **Decision**: Both the zero-shot arm and the few-shot arm submit their
  prompts through `anthropic.Anthropic().messages.create(...)`. The harness is
  blind to which arm is running — it only compares numeric outcomes.
- **Rationale**: The kata's measurable claim is that *the same model, called
  the same way, changes behavior when you pre-condition it with 2–4 examples*.
  Using a single client path keeps the independent variable to the prompt
  contents only (US1 Independent Test, US2 Acceptance Scenario 1).
- **Alternatives considered**:
  - *Hand-written HTTP client.* Rejected: adds surface area without changing
    the signal under study.
  - *A higher-level orchestration framework (LangChain / LlamaIndex).*
    Rejected: hides the prompt structure the kata is specifically teaching the
    practitioner to see.

### D-002 — Pydantic v2 for every structured boundary

- **Decision**: `ExamplePair`, `ExampleSet`, `FewShotPrompt`,
  `CalibrationReport`, and `ConsistencyMetric` are pydantic v2 models. The
  `ExampleSet.pairs` field carries `min_length=2, max_length=4` (FR-006), and
  `ExampleSet` registers a `model_validator(mode="after")` that detects
  contradictory input-prefix/output-field clashes and raises
  `ContradictoryExamplesError` (FR-005, SC-003).
- **Rationale**: Constitution Principle II (NON-NEGOTIABLE). The kata's
  integrity hinges on a contradiction being *unignorable*; a typed validator
  is the only path that guarantees that.
- **Alternatives considered**:
  - *Plain dicts / TypedDict.* Rejected: no runtime enforcement, silently
    accepts a 5-pair set or a contradiction.
  - *Post-hoc assertion after construction.* Rejected: easy to forget in one
    code path; validators can't be forgotten — they run on construct.

### D-003 — Static-prefix / dynamic-suffix prompt composition (Kata-10 compatible)

- **Decision**: `FewShotBuilder.build(example_set, target_input)` emits the
  prompt as `[stable prefix: system instructions + example block]` followed by
  `[dynamic suffix: target input]`. The stable prefix is identical across
  every corpus input for a given `example_set_id`.
- **Rationale**: Constitution Principle III (Context Economy). This ordering
  is required to make Kata 10's prefix-caching strategy applicable to few-shot
  calls — the example block is the *ideal* prefix-cache candidate because it
  is long, identical across many calls, and rarely changes. Cross-reference:
  `specs/010-prefix-caching/`.
- **Alternatives considered**:
  - *Interleave target input between examples ("chat-style").* Rejected:
    destroys the cacheable prefix and gains nothing measurable for a static
    task format.
  - *Put examples after the target input.* Rejected: loses attention weight on
    the examples and is the documented anti-pattern for format steering.

### D-004 — Declared inconsistency-reduction target: **40% relative**

- **Decision**: SC-001's declared `X%` reduction target is set to **40%
  relative** reduction in inconsistency rate (baseline rate × 0.60 or better
  after calibration). The harness fails the build if
  `inconsistency_few_shot > 0.60 * inconsistency_zero_shot` on the fixture
  corpus.
- **Rationale**: The spec requires a numeric threshold to make "significant
  improvement" falsifiable. 40% relative is aggressive enough to reject
  accidental ties (zero-shot already happened to work today) and attainable
  enough on a curated 10-input informal-measures corpus with a 3-pair
  calibrated set. It is documented as a *declared* target, not an absolute
  law — later katas may tighten it.
- **Alternatives considered**:
  - *Absolute threshold (e.g. "final inconsistency ≤ 10%").* Rejected: depends
    too heavily on corpus difficulty and punishes corpora chosen to expose
    edge cases.
  - *Purely statistical (p-value on paired outcomes).* Rejected: overkill for
    a 10-input corpus; encodes more machinery than the lesson.

### D-005 — Inconsistency = schema-invalid OR expected-value-mismatch

- **Decision**: A single corpus run contributes one boolean per input to the
  `ConsistencyMetric`: `inconsistent = (not schema_valid) or
  expected_value_mismatch`. The `inconsistency_rate` is the arithmetic mean of
  those booleans over the corpus.
- **Rationale**: Operationalizes SC-002 (100% schema-valid on calibrated
  runs) and SC-001 (measurable delta) with one metric that is comparable
  between arms. The harness never inspects free prose — only (a) pydantic
  validation against the declared output schema and (b) an equality / tolerance
  check against the labelled expected value.
- **Alternatives considered**:
  - *Separate schema-validity and value-match deltas.* Deferred: useful
    diagnostically, but SC-001 asks for *one* headline delta; the
    `CalibrationReport` still reports the two components individually for
    audit.
  - *Model-graded consistency (LLM-as-judge).* Rejected: circular, and
    Principle I forbids signal-over-prose control.

### D-006 — ExampleSetRegistry with explicit rotation

- **Decision**: A `ExampleSetRegistry` catalogs named example sets by id
  (`"calibrated"`, `"alternate"`, `"contradictory"`, `"overlong"`, plus the
  reserved `"zero_shot"` for the baseline arm). `harness.run()` takes an
  `example_set_id` argument and stamps it onto every `CalibrationReport` and
  every output trace line (FR-003, SC-004). US3 iterates across ids and
  records each arm's rate.
- **Rationale**: Rotating example sets is only educational if *which set was
  active* is machine-readable per result. A registry makes that a typed field
  instead of a comment.
- **Alternatives considered**:
  - *Pass an inline `ExampleSet` and hash it for an id.* Rejected: obscures
    provenance; human-readable ids matter for the kata's narrative.
  - *Git-tracked YAML catalog.* Deferred: small enough to ship as JSON
    fixtures inside `tests/.../fixtures/`; YAML adds a dependency for no gain.

### D-007 — Anti-pattern acknowledgement flag for zero-shot runs

- **Decision**: `harness.run(..., acknowledge_zero_shot=False)` on a task
  tagged `subjective=True` in the task registry raises
  `ZeroShotOnSubjectiveTaskError`. The baseline arm in the measurement harness
  passes `acknowledge_zero_shot=True` explicitly, creating an audit record
  that the zero-shot run was deliberate (FR-007).
- **Rationale**: Makes the defended anti-pattern (silent zero-shot on a
  subjective task) structurally impossible. Matches Constitution Principle VI
  (Human-in-the-Loop Escalation) — any action outside the declared safe
  envelope halts unless explicitly authorized.
- **Alternatives considered**:
  - *Runtime warning only.* Rejected: warnings are ignored in automation;
    the spec wants the anti-pattern *defeated*, not merely annotated.
  - *Disallow zero-shot outright.* Rejected: impossible to *measure* the
    calibration delta without running zero-shot at least once per corpus.

### D-008 — Over-long example size guard + leakage-candidate flag

- **Decision**: `validators.size_guard(example_set)` fails construction if any
  serialized `ExamplePair` exceeds a declared byte budget (default: 2048
  bytes per pair, configurable). `validators.flag_leakage_candidate(pair)`
  emits a non-fatal warning on the `CalibrationReport.warnings` list when a
  pair matches a known-canonical pattern (exact-match against a small
  shortlist; operators review).
- **Rationale**: Covers Edge Case #4 (examples dominate context budget) and
  Edge Case #2 (example appears to leak memorized training data). The size
  guard is fatal because its failure mode is silent — the target input gets
  pushed out of attention. The leakage flag is non-fatal because judgement is
  needed; operators review the flagged run.
- **Alternatives considered**:
  - *Token counting instead of bytes.* Deferred: adds a tokenizer dependency
    for marginal gain; bytes is a conservative proxy and matches
    fixture-replayability.
  - *Hard reject on leakage.* Rejected: false positives on small corpora
    would block useful sets; non-fatal flag + audit trail is the calibrated
    response.

### D-009 — Recorded fixtures as the default; `LIVE_API=1` is opt-in

- **Decision**: The default `pytest` run loads fixtures from
  `tests/katas/014_few_shot_calibration/fixtures/` via an injectable
  `RecordedClient`. `LIVE_API=1` swaps in the real SDK for the same corpus
  and records a fresh `CalibrationReport`.
- **Rationale**: Matches the shared baseline and keeps the CI offline +
  deterministic (Principle V). The LIVE_API path is the demonstration path —
  proves the calibration works against the actual model — but is not the
  default teaching-mode path.
- **Alternatives considered**:
  - *VCR.py cassettes.* Rejected as overkill for ~30 recorded calls; plain
    JSON fixtures remain teaching-legible.
  - *Mocking the SDK.* Rejected: couples tests to SDK internals rather than
    to the kata's observable contract.

## Inconsistency-Reduction Target (declared for SC-001)

| Arm | Corpus | Metric | Declared target |
|-----|--------|--------|-----------------|
| zero-shot baseline | `corpus_informal_measures.json` (10 inputs) | `inconsistency_rate = mean(not schema_valid or value_mismatch)` | record only |
| few-shot (calibrated set, 3 pairs) | same 10 inputs | same metric | `inconsistency_few_shot ≤ 0.60 × inconsistency_zero_shot` **AND** `schema_valid == True` for 100% of few-shot outputs (SC-002) |
| few-shot (alternate set, 2–4 pairs) | same 10 inputs | same metric | record only; exists for US3 / SC-004 sensitivity |

The 40% relative-reduction target is encoded as a constant in
`katas/014_few_shot_calibration/harness.py` (`INCONSISTENCY_REDUCTION_TARGET =
0.40`) and as a field on `CalibrationReport.target_relative_reduction` so the
number is reproduced in every report. Raising or lowering the target is a
single-point change, audited by git history.

## Tessl Tiles

`tessl search few-shot` and `tessl search prompt-calibration` (run 2026-04-23)
returned no tiles matching the Python-side calibration / measurement domain.
Closest hits were unrelated prompt-engineering UX skills. **No tiles installed
for this feature.**

Follow-up: if a community tile for few-shot prompt composition against the
Anthropic Messages API later appears (search terms: `few-shot-anthropic`,
`prompt-examples`, `in-context-learning`), revisit at Kata 15 plan time. No
eval scores recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION surface from the spec has been resolved:

- "declared X%" in SC-001 → resolved to **40% relative reduction** (D-004).
- "inconsistency rate" definition → resolved to "schema-invalid OR
  expected-value-mismatch, arithmetic mean over corpus" (D-005).
- "subjective / format-sensitive task" tagging → resolved via task-registry
  `subjective=True` flag used by the anti-pattern guard (D-007).
