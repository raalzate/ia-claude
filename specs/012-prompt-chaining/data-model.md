# Phase 1 Data Model: Multi-Pass Prompt Chaining

All entities below are implemented as pydantic v2 models under
`katas/012_prompt_chaining/`. Validation runs on construction AND at every
stage boundary (input read, output write). Any invalid payload raises — no
best-effort path — in keeping with Constitution Principle II and FR-004.

## MacroTask

The overall audit objective handed to the `Chain` orchestrator.

| Field | Type | Notes |
|-------|------|-------|
| `task_id` | `str` (UUID4) | Used as the `runs/` subdirectory name. |
| `objective` | `str` | Human-readable audit objective (e.g. "audit this 15-file PR"). |
| `corpus` | `list[FileRef]` | Ordered references to the input files. One file = one per-file stage report. |
| `declared_stages` | `list[StageDefinition]` | Ordered list of stage declarations; identifies class, order, and per-stage budget. |
| `created_at` | `datetime` (UTC) | Populated at construction. |

**Invariants**
- `corpus` is non-empty (edge case "very few files" is explicitly modeled, but
  a zero-file task is rejected at construction time).
- `declared_stages` contains at least `PerFileAnalysisStage` and
  `IntegrationAnalysisStage` in that order for the MVP chain; the extension
  case (US3) appends additional stages WITHOUT removing or reordering the
  first two.

## FileRef

| Field | Type | Notes |
|-------|------|-------|
| `path` | `str` | Path relative to the corpus root. |
| `content_hash` | `str` (sha256) | Anchors provenance of every derived finding (Principle VII). |
| `size_bytes` | `int` | Used for edge-case logging only; not a budget gate. |

## StageDefinition (declaration — distinct from `ChainStage` runtime instance)

Serializable record of a stage as declared on a `MacroTask`. Used for audit
logs and extension-diff checks.

| Field | Type | Notes |
|-------|------|-------|
| `stage_index` | `int` (≥ 0) | Zero-indexed position in the chain. |
| `name` | `str` | Matches the `ChainStage.name` of the runtime instance. |
| `responsibility` | `str` | The single responsibility the stage prompt may address (FR-003). |
| `max_prompt_tokens` | `int` (> 0) | Declared token budget (FR-003, SC-002). |
| `input_schema_ref` | `str` | Dotted path to the pydantic input-schema class. |
| `output_schema_ref` | `str` | Dotted path to the pydantic output-schema class. |

## ChainStage (abstract runtime base class)

Defined at `katas/012_prompt_chaining/stages/base.py`. Subclasses implement
`run`.

| Field / method | Type | Notes |
|----------------|------|-------|
| `name` | `str` | Matches its `StageDefinition.name`. |
| `responsibility` | `str` | Matches its `StageDefinition.responsibility`. |
| `input_schema` | `type[BaseModel]` | Validated against the incoming payload; mismatch → `MalformedIntermediatePayload` (FR-004). |
| `output_schema` | `type[BaseModel]` | Validated against the stage's return value before persistence (FR-004, Principle II). |
| `max_prompt_tokens` | `int` | Enforced before SDK call; overflow → `StageBudgetExceeded` (FR-003, SC-002). |
| `run(input: BaseModel) -> BaseModel` | `abstractmethod` | Emits an instance of `output_schema`. Raises on internal failure (never silent). |

### Concrete subclasses

- **`PerFileAnalysisStage`** — `input_schema=MacroTask`, `output_schema=
  PerFileBundle`. Emits one `PerFileReport` per `FileRef` in the corpus, plus
  any `PerFileAnalysisFailure` entries (see below). Its prompt MUST restrict
  itself to local, file-scoped analysis (FR-003).
- **`IntegrationAnalysisStage`** — `input_schema=PerFileBundle`,
  `output_schema=FinalReport`. Reads ONLY the `PerFileBundle` (never the raw
  corpus); its prompt MUST restrict itself to inter-module coherence
  (FR-003, US1-AS2, US1-AS3). If the input bundle contains any
  `PerFileAnalysisFailure` entries, the stage refuses to run (FR-008, SC-003).
- **`SecurityScanStage`** *(US3 demo extension — not part of MVP chain)* —
  `input_schema=PerFileBundle`, `output_schema=SecurityReport`. Added to the
  stage list without modifying `PerFileAnalysisStage` or
  `IntegrationAnalysisStage` source (FR-005, SC-004).

## IntermediatePayload (family of pydantic models persisted at each boundary)

Every payload persisted at `runs/<task_id>/stage-<n>.json` carries these
common header fields plus the stage-specific body:

| Field | Type | Notes |
|-------|------|-------|
| `task_id` | `str` | Echoes `MacroTask.task_id`. |
| `stage_index` | `int` (≥ 0) | The originating stage's index (FR-007). |
| `stage_name` | `str` | The originating stage's name (FR-007, US1-AS? traceability). |
| `emitted_at` | `datetime` (UTC) | When the payload was written. |
| `body` | `BaseModel` | The stage-specific output (e.g. `PerFileBundle`, `FinalReport`). |

### Stage-specific bodies

- **`PerFileBundle`** — emitted by `PerFileAnalysisStage`. Fields:
  `reports: list[PerFileReport]`, `failures: list[PerFileAnalysisFailure]`.
- **`PerFileReport`** — fields: `file_path`, `file_content_hash`, `findings:
  list[LocalFinding]`. `file_content_hash` back-references the original
  `FileRef.content_hash` for provenance (Principle VII).
- **`LocalFinding`** — fields: `finding_id`, `severity`, `description`,
  `originating_stage: Literal["per_file"]`.
- **`PerFileAnalysisFailure`** — fields: `file_path`, `file_content_hash`,
  `error_category` (`"timeout" | "parse_error" | "tool_failure" |
  "other"`), `message`.
- **`FinalReport`** — emitted by `IntegrationAnalysisStage`. Fields:
  `inter_module_findings: list[IntegrationFinding]`,
  `references_per_file_reports: list[str]` (list of `PerFileReport.file_path`
  values the integration cited). MUST NOT contain any single-file local
  issue already present in the upstream `PerFileBundle` (US1-AS3, enforced at
  validate time by cross-checking finding IDs).
- **`IntegrationFinding`** — fields: `finding_id`, `severity`, `description`,
  `involved_files: list[str]` (≥ 2), `originating_stage:
  Literal["integration"]`.
- **`SecurityReport`** *(US3 demo extension)* — fields:
  `vulnerabilities: list[SecurityFinding]`, each with `originating_stage:
  Literal["security"]`.

## StageBudgetExceeded (exception)

Raised by the orchestrator BEFORE calling the SDK when the assembled prompt
exceeds the stage's declared `max_prompt_tokens`.

| Field | Type | Notes |
|-------|------|-------|
| `stage_index` | `int` | Which stage blew its budget. |
| `stage_name` | `str` | For log readability. |
| `declared_budget` | `int` | The stage's `max_prompt_tokens`. |
| `measured_tokens` | `int` | The tokenized prompt's actual size. |
| `overflow` | `int` | `measured_tokens - declared_budget`. |

Not recoverable by the orchestrator — always halts the chain (FR-003).

## MalformedIntermediatePayload (exception)

Raised when a stage's output fails its own `output_schema` OR the downstream
stage's `input_schema`.

| Field | Type | Notes |
|-------|------|-------|
| `stage_index` | `int` | The stage that produced the bad payload. |
| `stage_name` | `str` | For log readability. |
| `validation_errors` | `list[dict]` | Serialized pydantic `ValidationError.errors()` list. |
| `payload_path` | `str` | `runs/<task_id>/stage-<n>.json`. |

Not recoverable by the orchestrator — always halts the chain (FR-004, SC-003).

## ChainRun (run-scoped aggregate, not persisted as a single blob)

Conceptual aggregate that the orchestrator exposes to callers:

| Field | Type | Notes |
|-------|------|-------|
| `task` | `MacroTask` | The input. |
| `stage_payloads` | `list[IntermediatePayload]` | One per completed stage; same ordering as `MacroTask.declared_stages`. |
| `final_report` | `FinalReport \| None` | Populated iff the integration stage ran to completion. |
| `halted` | `HaltRecord \| None` | Populated iff the chain halted before completion. |

### HaltRecord

| Field | Type | Notes |
|-------|------|-------|
| `cause` | `Literal["stage_budget_exceeded", "malformed_intermediate_payload", "per_file_analysis_failure"]` | Closed set — never free text. |
| `stage_index` | `int` | The stage where the halt occurred. |
| `detail` | `dict` | Structured detail from the raising exception. |

## Relationships

```
MacroTask
  ├── corpus: [FileRef]
  ├── declared_stages: [StageDefinition]
  └── run outputs:
        stage-0.json  → IntermediatePayload{body=PerFileBundle}
                         ├── reports:  [PerFileReport → LocalFinding]
                         └── failures: [PerFileAnalysisFailure]
        stage-1.json  → IntermediatePayload{body=FinalReport}
                         └── inter_module_findings: [IntegrationFinding]
        (US3) stage-2.json → IntermediatePayload{body=SecurityReport}
```

## What is deliberately NOT modeled

- Retry budgets / backoff — per-file failures halt the chain loud (FR-008).
- Parallel per-file execution — sequential is clearer pedagogy and matches
  the "accumulated payload" semantics of FR-002.
- Cost-based budget — `max_prompt_tokens` is the kata's teachable gate
  (SC-002).
- Cross-session state — one `MacroTask` = one run directory.
