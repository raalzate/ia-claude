# Phase 0 Research: Multi-Pass Prompt Chaining

## Decisions

### D-001 — `ChainStage` as a pydantic-abstract-base class

- **Decision**: Every stage subclasses `ChainStage`, a pydantic model whose
  required attributes are `name: str`, `responsibility: str`, `input_schema:
  type[BaseModel]`, `output_schema: type[BaseModel]`, `max_prompt_tokens: int`,
  and an abstract `run(input: BaseModel) -> BaseModel` method. The `Chain`
  orchestrator consumes an ordered `list[ChainStage]`.
- **Rationale**: FR-001 demands explicitly declared stages with named
  responsibilities; Principle II demands schema-enforced boundaries. Making the
  schema classes themselves first-class fields on the base class forces every
  stage author to declare both ends of its I/O contract. This is also what
  makes FR-005 / SC-004 achievable: extension is "append a new `ChainStage`
  subclass to the ordered list."
- **Alternatives considered**:
  - *Plain Python callables registered in a list.* Rejected: nothing forces
    declaration of the input/output schemas, so Principle II becomes
    aspirational instead of mechanical.
  - *ABC (`abc.ABC`) without pydantic.* Rejected: loses the runtime validation
    on schema attributes themselves, pushing errors to stage-run time instead
    of instantiation time.
  - *Framework (LangChain `Chain`, Haystack `Pipeline`).* Rejected: hides
    stage-boundary validation behind internal plumbing — directly undermines
    the kata's teaching value.

### D-002 — Concrete stages: `PerFileAnalysisStage`, `IntegrationAnalysisStage`, `SecurityScanStage`

- **Decision**: Ship two stages for the MVP chain (`PerFileAnalysisStage`,
  `IntegrationAnalysisStage`) and one demo extension stage
  (`SecurityScanStage`) used ONLY by the User-Story-3 extension test. The
  extension stage lives in the `stages/` sub-package and is wired into the
  chain only by test-side factory code.
- **Rationale**: Directly serves US1 (MVP chain) and US3 (extensibility). The
  diff-based test (SC-004) becomes trivial: adding `security.py` and appending
  it to the stage list must not modify `per_file.py` or `integration.py`.
- **Alternatives considered**:
  - *Include security stage in the default chain.* Rejected: muddles US1's
    independent test ("exactly N per-file reports plus one integration
    report").

### D-003 — Size-budget gate via `max_prompt_tokens` + `StageBudgetExceeded`

- **Decision**: Each `ChainStage` declares a `max_prompt_tokens` integer. Before
  calling the SDK, the orchestrator tokenizes the assembled prompt with
  `tiktoken` (local, deterministic) and raises `StageBudgetExceeded` if it
  exceeds the declared budget. The chain halts with the stage index and the
  measured overflow.
- **Rationale**: FR-003 requires the prompt to stay scoped to the stage's
  declared responsibility; SC-002 makes this measurable. A typed exception
  (not a log warning, not a truncation) is the only mechanism consistent with
  Principles I and VI: the build fails loud, and a human decides what to do.
- **Alternatives considered**:
  - *Rely on the API's own 400-type error for over-context input.* Rejected:
    couples the budget gate to model-specific limits and only fires after
    burning a round trip.
  - *Truncate the payload automatically.* Rejected: silent degradation — the
    exact anti-pattern Principle III / VI warn against.

### D-004 — Intermediate payload persistence as per-stage JSON files

- **Decision**: The orchestrator writes `runs/<session-id>/stage-<n>.json`
  after each stage boundary. The file is the serialized `IntermediatePayload`.
  Downstream stages read it back and `model_validate` against their own
  declared `input_schema`. Malformed payloads (missing fields, schema
  mismatch) raise `MalformedIntermediatePayload` and halt the chain.
- **Rationale**: FR-002 (persist intermediate payloads), FR-004 (fail loud on
  malformed payload), FR-007 (per-artifact traceability to originating stage)
  all fall out of per-stage JSON files with a `stage_name` + `stage_index`
  header field. Principle VII (Provenance & Self-Audit) is satisfied because
  the run directory is the complete audit trail.
- **Alternatives considered**:
  - *In-memory-only payloads.* Rejected: loses replayability, breaks
    Principle VII.
  - *SQLite run database.* Rejected: query surface irrelevant for the kata;
    JSON per stage is the minimum that satisfies audit.

### D-005 — Fail-loud semantics for malformed payloads AND per-file failures

- **Decision**: Two distinct, typed halts:
  1. `MalformedIntermediatePayload` — raised when a stage's output fails its
     own `output_schema` OR the downstream stage's `input_schema`. Halts the
     chain with the offending stage index.
  2. `PerFileAnalysisFailure` — a first-class entry inside the
     `IntermediatePayload` emitted by `PerFileAnalysisStage` when one file's
     analysis errors. The integration stage sees the error entry explicitly;
     if any error entries are present, the chain halts before calling the
     integration stage — no silent partial integration.
- **Rationale**: FR-004 and FR-008 + SC-003 require zero silent swallowing.
  Making the failure a typed entry in the payload (rather than a missing
  entry) means the chain can still audit-trail the failure while refusing to
  proceed.
- **Alternatives considered**:
  - *Treat per-file failure as "best-effort, continue with N-1 reports".*
    Rejected: directly violates FR-008.
  - *Retry the failing file.* Rejected: out of scope — retries belong to a
    later kata and would hide the saturation signal the kata is teaching.

### D-006 — Baseline-vs-chain comparison fixture + coverage-delta target

- **Decision**: Ship a 15-file PR fixture corpus at
  `tests/katas/012_prompt_chaining/fixtures/corpus_15_files/`. Two recorded
  runs are stored alongside:
  - `baseline_monolithic.json` — single monolithic prompt result over the
    entire corpus.
  - `chain_happy_path.json` — chained-run result over the same corpus.
  The integration test `test_baseline_vs_chain.py` loads both, computes the
  finding-coverage delta, and asserts `chain_count >= baseline_count +
  COVERAGE_DELTA_TARGET`.
- **Coverage-delta target**: `COVERAGE_DELTA_TARGET = 3` distinct findings.
  Declared here per SC-001 ("at least the declared delta"). The number is
  chosen so that the baseline's demonstrable drop-offs on a 15-file corpus
  (typically inter-module inconsistencies the monolithic prompt dilutes) must
  be recovered by at least three concrete findings in the chained run.
  Rationale for the specific value: empirically tractable on a 15-file corpus
  without turning the test into a perf benchmark; large enough that an
  accidentally-weakened chain (e.g. integration prompt leaking per-file
  concerns) will fail the assertion. Reviewable and adjustable in the kata's
  README reflection if future runs justify it.
- **Alternatives considered**:
  - *Delta measured as a percentage of baseline findings.* Rejected: on small
    corpora a single missed finding can push percentages wildly; an absolute
    count is both clearer pedagogy and more stable.
  - *No baseline at all — assert only "chain produces ≥ 1 integration-only
    finding".* Rejected: US2 exists precisely to make the anti-pattern's cost
    visible, and SC-001 is explicit about the comparison.

### D-007 — Recorded fixtures over live API calls in tests

- **Decision**: All acceptance and integration tests run offline against
  recorded JSON fixtures under
  `tests/katas/012_prompt_chaining/fixtures/`. Live SDK calls are gated
  behind `LIVE_API=1` and not part of CI, matching the shared baseline and
  the Kata-1 precedent.
- **Rationale**: Determinism (Principle I), offline reproducibility, and zero
  API-quota burn in CI. The tests verify chain control flow and payload
  contracts, not model output quality — recordings are the correct fixture.
- **Alternatives considered**:
  - *VCR.py cassettes.* Rejected: overkill for the fixture set; plain JSON
    loaded by a stub client is clearer teaching code.

### D-008 — Extension test via source-diff, not behavioral assertion

- **Decision**: `test_chain_extension_diff.py` reads the content of
  `stages/per_file.py` and `stages/integration.py` before and after the
  extension scenario (adding `SecurityScanStage` and running the chain with
  the extended list). It asserts byte-identical content for the earlier stage
  files.
- **Rationale**: SC-004 demands "zero changes to existing stage definitions,
  prompts, or payload contracts (verified by diff)". A behavioral test could
  pass even if a maintainer had added a compatible edit to an earlier stage;
  a literal diff gate is the only durable defense.
- **Alternatives considered**:
  - *Rely on `git diff` in CI.* Rejected: couples the kata to VCS tooling
    instead of expressing the invariant in code the student can read.

## Coverage-Delta Target

- Name: `COVERAGE_DELTA_TARGET`
- Value: **3 distinct findings**
- Locked in: `test_baseline_vs_chain.py` constant + documented in the kata
  README reflection section.
- Justification: see D-006.

## Tessl Tiles

`tessl search prompt-chaining` and `tessl search chain-of-thought` (run
2026-04-23) returned no tiles covering orchestrator-style prompt chaining or
stage-boundary schema validation for the Anthropic Python SDK. Closest hits
were unrelated skill tiles. **No tiles installed for this feature.** No eval
scores recorded.

Follow-up: if a community tile covering typed prompt-chain orchestration
later appears (search terms: `prompt-chain`, `multi-pass`, `stage-schema`),
revisit at the next plan-phase review cycle. Until then, the orchestrator is
hand-rolled inside `katas/012_prompt_chaining/`.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION in the spec (zero) is resolved by the
decisions above. The coverage-delta target is explicitly declared (D-006) so
SC-001 is measurable out of the gate.
