# Phase 0 Research: Agentic Loop & Deterministic Control

## Decisions

### D-001 — Use the official `anthropic` Python SDK

- **Decision**: Drive the loop through `anthropic.Anthropic().messages.create(...)`
  and read the response's `.stop_reason` attribute directly.
- **Rationale**: The kata's whole point is that `stop_reason` is a first-class
  structured field on the API response. Using the SDK guarantees the field is
  typed and stable across model versions; rolling a custom HTTP client would
  reimplement this for no teaching value.
- **Alternatives considered**:
  - *Raw `httpx` + hand-written JSON parser.* Rejected: adds surface area without
    changing the signal the kata is exercising.
  - *LangChain / LlamaIndex abstraction.* Rejected: hides `stop_reason` behind
    framework callbacks, directly undermining the kata's pedagogy.

### D-002 — Pydantic v2 models for every structured boundary

- **Decision**: `ToolDefinition`, `ToolCall`, `ToolResult`, and `EventRecord`
  are pydantic v2 models. Tool registration and event-log emission both go
  through `model_validate` / `model_dump_json`.
- **Rationale**: Constitution Principle II (Schema-Enforced Boundaries,
  NON-NEGOTIABLE). Invalid payloads raise immediately; there is no "best effort"
  path to hide a malformed tool-use block.
- **Alternatives considered**:
  - *TypedDict / plain dicts.* Rejected: no runtime enforcement, silently accepts
    garbage — direct Principle II violation.
  - *dataclasses.* Rejected: no validation out of the box, would need bolt-on
    validation that duplicates pydantic's work.

### D-003 — Append-only JSONL event log

- **Decision**: One JSONL file per run at `runs/<session-id>/events.jsonl`.
  Each line is an `EventRecord` serialized with `model_dump_json`.
- **Rationale**: Principle VII (Provenance & Self-Audit) wants the trajectory
  replayable from the log alone. JSONL is the simplest append-only format that
  survives crashes and is trivially greppable / replayable.
- **Alternatives considered**:
  - *SQLite.* Rejected: query surface irrelevant for a one-shot reconstruction;
    adds deployment friction to a workshop.
  - *Structured logging through `logging` module.* Rejected: formatter and
    handler configuration is a distraction and silently drops records when the
    root logger is reconfigured elsewhere.

### D-004 — Recorded fixtures over live API calls in tests

- **Decision**: Ship VCR-style JSON fixtures under
  `tests/katas/kata_001_agentic_loop/fixtures/` and inject a `RecordedClient` that
  returns them. Live SDK calls are gated behind an env var (`LIVE_API=1`) and
  are not part of the default test run.
- **Rationale**: Determinism and offline reproducibility. The tests verify
  *control flow* over structured signals, not model output quality — a recording
  is the correct fixture. Also keeps CI free of API quota usage.
- **Alternatives considered**:
  - *VCR.py cassettes.* Rejected as overkill for the tiny fixture set here;
    plain JSON loaded by a stub client is clearer as teaching code.
  - *Stub the SDK with mocks.* Rejected: couples tests to the SDK's internals
    rather than to the observable stop-signal contract.

### D-005 — AST-based lint to forbid prose matching

- **Decision**: A test at `tests/katas/kata_001_agentic_loop/lint/test_no_prose_matching.py`
  parses `katas/kata_001_agentic_loop/loop.py` with the `ast` module and fails if it
  finds: `import re`, `from re import ...`, a `str.find` call, or an `in`
  operator where the right-hand side is a `str` literal. This operationalizes
  FR-004 as a machine-checkable gate.
- **Rationale**: Constitution Principle I is absolute — "regex-on-prose" bugs
  re-enter codebases during maintenance. A test that fails the build is the
  only durable defense. Teaches the kata's core lesson at CI level.
- **Alternatives considered**:
  - *Code review only.* Rejected: human review drift is exactly what the
    constitution warns against.
  - *ruff / flake8 custom rule.* Deferred: can be layered later; the ast test
    is enough for MVP.

### D-006 — Single project layout; 20 katas as sibling packages

- **Decision**: All katas live under `katas/kata_NNN_<slug>/`; tests under
  `tests/katas/kata_NNN_<slug>/`; per-kata README alongside source.
- **Rationale**: FDD cadence (Constitution v1.2.0 Development Workflow) is
  easier when each kata is a self-contained package that can be graded in
  isolation. Avoids premature shared libraries that would couple katas.
- **Alternatives considered**:
  - *Monorepo with shared `common/` package.* Rejected until a second kata
    actually needs to share something — otherwise it violates YAGNI.
  - *Separate repos per kata.* Rejected: complicates dashboard and iikit state
    tracking.

## Tessl Tiles

`tessl search anthropic` (run 2026-04-23) returned 20 results, none covering
the Python `anthropic` SDK control-flow domain. Closest hits were unrelated
skills (brand-guidelines, cybersecurity). **No tiles installed for this feature.**

Follow-up: if a community tile for the Anthropic Python SDK later appears
(search terms: `anthropic-sdk-python`, `messages-api`), revisit at kata 2 plan
time. No eval scores recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION from the spec (there were 0) has been resolved
by the decisions above.
