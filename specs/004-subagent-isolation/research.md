# Phase 0 Research: Strict Subagent Context Isolation (Hub-and-Spoke)

## Decisions

### D-001 — `Coordinator` and `Subagent` as separate Python modules behind a `TaskSpawner` protocol

- **Decision**: Coordinator lives at `katas/004_subagent_isolation/coordinator.py`,
  Subagent at `katas/004_subagent_isolation/subagent.py`. The Coordinator
  holds a `task_spawner: TaskSpawner` attribute (a Protocol declared in
  `task_spawner.py`) whose `.spawn(payload: SubtaskPayload) -> SubagentResult`
  is the only path from coordinator to subagent.
- **Rationale**: Principle IV (Subagent Isolation) requires a visible
  architectural boundary — not just a convention. Separate modules give the
  AST lint (see D-005) a real import graph to inspect. The Protocol-based
  `TaskSpawner` makes FR-008 / SC-003 (swap one subagent without touching the
  coordinator) a pure dependency-injection exercise rather than a subclassing
  maneuver.
- **Alternatives considered**:
  - *Single module with two classes.* Rejected: defeats the AST lint, which
    needs a distinct file to forbid imports from.
  - *Subclass-based dispatch (`class WeatherSubagent(Subagent)`).* Rejected:
    invites shared base-class state that would silently re-inherit coordinator
    context — exactly the anti-pattern the kata defends against.

### D-002 — Pydantic v2 models for every handoff boundary

- **Decision**: `SubtaskPayload`, `SubagentResult`, and `HandoffContract` are
  pydantic v2 models with `model_config = ConfigDict(extra="forbid")`. The
  `Subagent.run()` method calls `SubtaskPayload.model_validate(...)` on
  input and `SubagentResult.model_validate_json(raw)` on output. The
  coordinator consumes only the validated `SubagentResult` instance, never
  the raw string.
- **Rationale**: Principle II (Schema-Enforced Boundaries, NON-NEGOTIABLE),
  FR-001, FR-003. `extra="forbid"` operationalizes spec Edge Case #2
  ("extra or unexpected fields [...] must be rejected"). Using the typed
  instance rather than the raw string makes FR-004 (terminal on validation
  failure, no silent fallback) a natural consequence rather than an extra
  guardrail.
- **Alternatives considered**:
  - *`dataclasses` + manual `json.loads`.* Rejected: no runtime enforcement;
    extra fields slip through — direct Principle II violation.
  - *TypedDict.* Rejected for the same reason; no validation at the boundary.

### D-003 — Per-run JSONL audit: `subagent_inputs.jsonl` + `subagent_outputs.jsonl`

- **Decision**: On every `.spawn(payload)` the Coordinator appends the serialized
  `SubtaskPayload` (one line) to `runs/<session_id>/subagent_inputs.jsonl`;
  on return it appends both the raw result string and the validated
  `SubagentResult.model_dump_json()` to
  `runs/<session_id>/subagent_outputs.jsonl`. Both files use
  `pydantic.model_dump_json` so the on-disk shape is byte-identical to the
  declared schema.
- **Rationale**: FR-005 requires an auditable diff of declared payloads vs.
  actual payloads. SC-001 and SC-004 are measured by scanning
  `subagent_inputs.jsonl` for the leak-probe UUID — a fixed audit surface is
  required. JSONL is append-only, crash-tolerant, and trivial to diff (same
  rationale as Kata 1 D-003).
- **Alternatives considered**:
  - *In-memory list captured by the test harness.* Rejected: would pass tests
    but give the student no real artifact to inspect after a live run, which
    undermines Principle VII (Provenance) and the kata's teaching goal.
  - *SQLite.* Rejected: query surface irrelevant for a one-shot audit; adds
    deployment friction.

### D-004 — Recorded fixtures for coordinator + subagent sessions; live API gated behind `LIVE_API=1`

- **Decision**: Ship VCR-style JSON fixtures under
  `tests/katas/004_subagent_isolation/fixtures/`. A `RecordedAnthropicClient`
  returns the canned `messages.create` response for each subagent spawn in
  sequence. Default `pytest` run is fully offline. A live end-to-end run is
  opt-in via `LIVE_API=1 python -m katas.004_subagent_isolation.runner`.
- **Rationale**: Determinism and CI cost, same reasoning as Kata 1 D-004.
  The tests verify **isolation and contract**, not model output quality — a
  recording is the correct fixture. Keeps CI free of API spend and flakiness.
- **Alternatives considered**:
  - *VCR.py cassettes.* Overkill for ≤ 8 fixtures.
  - *Mock the SDK.* Rejected: couples tests to SDK internals; a recorded
    client mirrors the observable contract (JSON in / JSON out).

### D-005 — AST + grep lint: `subagent.py` MUST NOT reference coordinator private history

- **Decision**: `tests/katas/004_subagent_isolation/lint/test_no_history_leak.py`
  parses `katas/004_subagent_isolation/subagent.py` with the `ast` module and
  fails the build if it finds (a) any `import` or `from` targeting
  `katas.004_subagent_isolation.coordinator`, (b) any `Attribute` node whose
  name matches `_history`, `_messages`, `_transcript`, `_scratchpad`, or
  `_private_history`, or (c) any string literal matching `"coordinator._history"`
  or equivalent. A simple grep pass (`rg`) across the same file is run as a
  belt-and-braces second check.
- **Rationale**: FR-002 ("System MUST reject any implicit inheritance of the
  coordinator's conversation history") and Principle IV are absolute; code
  review drift is exactly what the constitution warns against (see Kata 1
  D-005). An AST-level gate that fails CI is the only durable defense.
- **Alternatives considered**:
  - *Code review only.* Rejected — drift re-enters on every refactor.
  - *Runtime check (e.g. monkeypatch `Coordinator.__getattribute__`).*
    Rejected: brittle, doesn't catch static references, and adds production
    code whose only purpose is self-policing.

### D-006 — Leak-probe integration test: UUID seeded into coordinator history, asserted absent from all subagent inputs

- **Decision**:
  `tests/katas/004_subagent_isolation/integration/test_leak_probe.py` generates
  a fresh UUID per test run, writes it into the coordinator's private history
  (as a prior user turn AND as a coordinator scratchpad note), runs a
  multi-subtask task through the `RecordedAnthropicClient`, then reads
  `runs/<session_id>/subagent_inputs.jsonl` line-by-line and asserts the UUID
  string does not appear in any serialized `SubtaskPayload`.
- **Rationale**: SC-001 ("Zero bytes of coordinator-private conversation
  history observable in any subagent's input payload") and SC-004 (leak-probe
  occurrence count equals zero) are measurable-at-runtime assertions. The
  UUID approach is the canonical instantiation of the spec's leak-probe
  design. Using a fresh UUID per run prevents accidental false-pass from a
  hard-coded probe that the implementation could (bug-style) special-case.
- **Alternatives considered**:
  - *Constant probe string.* Rejected: an implementer could filter it out
    specifically and pass the test while leaking other state.
  - *Diff entire coordinator history against each payload.* Deferred: the
    UUID probe is a strictly stronger guarantee for the fixture corpus and
    much cheaper to assert; a full-diff audit can be layered later.

## Tessl Tiles

`tessl search "subagent isolation"` and `tessl search "hub and spoke agent"`
(run 2026-04-23) returned 0 tiles matching the Python + pydantic + Anthropic
SDK domain. **No tiles installed for this feature.** Follow-up: if a
community tile for subagent orchestration appears (search terms:
`subagent`, `hub-spoke`, `task-spawner`), revisit before `/iikit-07-implement`.

## Unknowns Carried Forward

None. Every requirement in `spec.md` (FR-001..FR-008, SC-001..SC-004, all five
Edge Cases) is covered by one of D-001..D-006 plus the data-model and
contracts produced in Phase 1.
