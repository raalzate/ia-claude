# Implementation Plan: Data Provenance Preservation

**Branch**: `020-data-provenance` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/020-data-provenance/spec.md`

## Summary

Build a Python kata under `katas/020_data_provenance/` that aggregates factual
claims across subagent-processed corporate manuals while preserving a 1:1
mapping between every emitted claim and its originating source. Each Subagent
extracts claims from one Source Document using an `anthropic.messages.create`
call whose `tools[0].input_schema` mirrors a pydantic `Claim` model: the four
provenance fields — `claim`, `source_url`, `source_name`, `publication_date` —
are required at the schema level, and `tool_choice={"type": "any"}` guarantees
tool extraction (no free prose). Subagents return a `SubagentClaimsPayload`
(validated per Principle IV), and a `ProvenanceAggregator` groups claims by a
canonical-claim-key (sha256 of normalized claim text), detecting disagreements
on numeric/factual content across sources. Conflicts are emitted as a
`ConflictSet` with `conflict_detected=true` and a companion `ReviewTask`; no
auto-resolution path exists (FR-003, FR-004, FR-005, SC-002). A post-aggregation
orphan-claim lint scans the emitted corpus and fails closed with
`OrphanClaimError` the instant any Claim is missing provenance (FR-002, SC-004).
Delivered under Constitution v1.3.0 principles II (NN — schema boundary),
IV (subagent isolation), VII (NN anchor — provenance self-audit), and
VIII (NN — mandatory docs).

## Technical Context

**Language/Version**: Python 3.11+ (matches Kata 1 baseline in
`specs/001-agentic-loop/plan.md` and Kata 4 baseline in
`specs/004-subagent-isolation/plan.md`).
**Primary Dependencies**:
- `anthropic` — each Subagent opens its own `anthropic.Anthropic().messages.create`
  call configured with a `Claim`-shaped tool (`input_schema` mirrors the
  `Claim` pydantic model) and `tool_choice={"type": "any"}` to guarantee the
  model emits a structured claim rather than a prose summary (FR-007).
- `pydantic` v2 — `Claim`, `ProvenanceRecord`, `Source`, `SubagentClaimsPayload`,
  `ConflictSet`, `AggregationReport`, and `ReviewTask` are pydantic models.
  The `Claim` model treats all four provenance fields as required at
  construction; missing fields → `pydantic.ValidationError` (FR-001, FR-002,
  Principle II NN). A custom validator documents the "internal-only"
  `source_url` path format (see Edge Cases §Internal-only identifier).
- `pytest` + `pytest-bdd` — BDD runner consumes `.feature` files produced by
  `/iikit-04-testify`. Plain `pytest` for unit + lint.
**Storage**: Local filesystem only. Per-run artifacts at `runs/<session-id>/`
(gitignored): `source_documents.jsonl` (one line per ingested manual),
`subagent_claims.jsonl` (one `SubagentClaimsPayload` per subagent spawn),
`aggregation_report.json` (the final `AggregationReport`), and
`review_tasks.jsonl` (one `ReviewTask` per detected conflict). These files
satisfy FR-006 (self-audit) and feed the SC-001 / SC-002 / SC-003 / SC-004
measurable outcomes.
**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit + lint.
Fixture subagent responses are recorded VCR-style JSON under
`tests/katas/020_data_provenance/fixtures/` and returned by a
`RecordedAnthropicClient` (same pattern as Kata 1 D-004 and Kata 4 D-004).
Live API runs are gated behind `LIVE_API=1`.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.
**Project Type**: Single project. Kata at `katas/020_data_provenance/`; tests
at `tests/katas/020_data_provenance/`. Mirrors the D-006 layout established
in `specs/001-agentic-loop/plan.md`.
**Performance Goals**: Not latency-bound. Recorded-fixture acceptance suite
completes in under 5 seconds locally (same target as Kata 1 and Kata 4).
**Constraints**:
- Every emitted `Claim` MUST have populated `claim`, `source_name`, and a
  `source_url`/`publication_date` pair that is either a real value or an
  explicitly typed nullable (`source_url: None` permitted for internal-only
  sources; `publication_date: None` permitted only for undated internal memos
  with an accompanying `publication_date_sentinel="unknown"` on the
  `ProvenanceRecord`). Silent acceptance of an absent field is a
  `pydantic.ValidationError`, never a coerced empty string (Principle II NN,
  FR-001, FR-002).
- The extraction tool's `input_schema` MUST be generated *from* the `Claim`
  pydantic model (via `Claim.model_json_schema()`), not hand-maintained, so a
  field addition on the pydantic model propagates automatically to the SDK
  call. Enforced by `tests/.../unit/test_tool_schema_mirrors_claim.py`.
- `tool_choice={"type": "any"}` MUST be set on every subagent extraction
  call. Enforced by `tests/.../unit/test_tool_choice_forces_extraction.py`
  inspecting the recorded client invocation arguments. This operationalises
  spec Edge Case §subagent-returns-prose and FR-007.
- The `ProvenanceAggregator` MUST NOT implement any "winner selection" code
  path — no recency filter, no majority vote, no model-internal preference
  (FR-004). Enforced by an AST lint
  (`tests/.../lint/test_no_auto_resolution.py`) that greps for forbidden
  symbols (`max`, `sort by date`, `pick_latest`, `majority_vote`,
  `confidence_score`) inside `aggregator.py`.
- The orphan-claim lint runs as the last step of every aggregation pass and
  raises `OrphanClaimError` on the first orphan encountered, blocking emission
  of the `AggregationReport` downstream (FR-002, SC-004).
**Scale/Scope**: One kata, ~500–700 LOC implementation + comparable test code;
one README; fixture corpus ≤ 8 recorded subagent sessions covering the
consistent-aggregation happy path, the seeded-contradictions anti-pattern,
missing-source-url (internal-only identifier), missing-publication-date
(fallback behavior), orphan-claim (must reject), and
duplicate-claim-different-sources.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Conflict detection and claim grouping branch on a deterministic canonical-claim-key (sha256 of normalized claim text) and on structured pydantic fields — never on the subagent's prose. `tool_choice={"type": "any"}` guarantees structured tool output; the aggregator never greps the model's response text. |
| II. Schema-Enforced Boundaries (NN) | `Claim`, `ProvenanceRecord`, `SubagentClaimsPayload`, `ConflictSet`, `AggregationReport`, `ReviewTask`, and `Source` are pydantic models with `model_config = ConfigDict(extra="forbid")`. The extraction tool's `input_schema` is generated from `Claim.model_json_schema()` so the SDK boundary and the pydantic boundary stay in lockstep. FR-001, FR-002, FR-007, FR-008. |
| III. Context Economy | Not load-bearing for this kata — payload size is dominated by the corpus being ingested, not by cache dynamics. The aggregator nonetheless logs only the canonical-claim-key and provenance metadata into the audit files, not full source text, to keep replay scans cheap. |
| IV. Subagent Isolation | Each Subagent processes **exactly one** Source Document in its own `anthropic.messages.create` session. The coordinator aggregates only the typed `SubagentClaimsPayload` returned by each subagent — it never reads a subagent's private conversation history. Mirrors the hub-and-spoke discipline from `specs/004-subagent-isolation/plan.md` (D-001, D-002). |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before any production code per Constitution v1.3.0 Development Workflow. Hashes will be locked in `.specify/context.json` before implement begins. |
| VI. Human-in-the-Loop | Every detected `ConflictSet` routes to a human via a `ReviewTask` — the pipeline explicitly does NOT emit a "winning" value (FR-004, FR-005). Schema-validation failures (`OrphanClaimError`, orphan `Claim`, malformed subagent payload) are terminal; the human reviewing the audit artifacts is the escalation target (Principle VI). |
| VII. Provenance & Self-Audit (NN anchor) | This kata is the constitutional anchor for Principle VII. Every emitted `Claim` carries a `ProvenanceRecord` (source_url, source_name, publication_date); every aggregation pass writes `aggregation_report.json` + `review_tasks.jsonl` + `subagent_claims.jsonl` so an auditor can replay which sources produced which claims, and whether any conflicts were surfaced (FR-006). SC-001 measures this at 100%. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function (the `Claim` validator, the tool-schema mirror, the canonical-claim-key hasher, the conflict detector, the orphan-claim lint) will carry a *why* comment tied to Principle VII or to the spec's anti-patterns. A single `notebook.ipynb` produced at `/iikit-07-implement` is the Principle VIII deliverable: it explains the kata, results, every Claude architecture concept exercised, the architecture walkthrough, applied patterns + principles, practitioner recommendations, the contract details, run cells, and the reflection. No separate `README.md`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/020-data-provenance/
  plan.md              # this file
  research.md          # Phase 0 output (D-001..D-007 + canonical-claim-key choice + Tessl note)
  data-model.md        # Phase 1 output (Source, Claim, ProvenanceRecord, ConflictSet, ReviewTask, SubagentClaimsPayload, AggregationReport)
  quickstart.md        # Phase 1 output (install, fixture run, scenario→spec map, §Kata Completion Standards checklist)
  contracts/           # Phase 1 output — JSON Schema Draft 2020-12, $id namespace kata-020
    claim.schema.json
    subagent-claims-payload.schema.json
    conflict-set.schema.json
    aggregation-report.schema.json
    review-task.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # already present
  # (kata narrative lives in katas/.../notebook.ipynb — no spec-side README)
```

### Source Code (repository root)

```text
katas/
  020_data_provenance/
    __init__.py
    models.py              # pydantic: Claim, ProvenanceRecord, Source, SubagentClaimsPayload, ConflictSet, ReviewTask, AggregationReport
    subagent.py            # Subagent.run(source: Source) -> SubagentClaimsPayload — opens fresh messages.create with Claim-shaped tool
    extraction_tool.py     # builds the tool definition from Claim.model_json_schema(); tool_choice={"type": "any"}
    aggregator.py          # ProvenanceAggregator: groups by canonical-claim-key, detects conflicts, emits ConflictSet + ReviewTask
    canonical_key.py       # sha256-based canonical-claim-key hashing (normalized text)
    orphan_lint.py         # post-aggregation check: OrphanClaimError on any claim missing provenance
    client.py              # thin injectable Anthropic client wrapper (mirrors Kata 1 D-001, Kata 4 D-004)
    runner.py              # CLI: `python -m katas.020_data_provenance.runner --manuals <path>...`
    notebook.ipynb         # Principle VIII deliverable — kata narrative + Claude architecture certification concepts (written during /iikit-07)

tests/
  katas/
    020_data_provenance/
      conftest.py
      features/
        data_provenance.feature        # produced by /iikit-04-testify
      step_defs/
        test_data_provenance_steps.py
      unit/
        test_claim_requires_all_provenance.py      # FR-001, FR-002, SC-004
        test_tool_schema_mirrors_claim.py          # extraction tool input_schema == Claim.model_json_schema()
        test_tool_choice_forces_extraction.py      # tool_choice={"type": "any"} on every spawn; FR-007
        test_canonical_key_stability.py            # same normalized text → same sha256 key
        test_aggregator_groups_by_key.py           # FR-008 (duplicates preserved) + grouping
        test_conflict_detection.py                 # FR-003, SC-002, SC-003 (recall on seeded conflicts)
        test_orphan_claim_rejection.py             # FR-002, SC-004 (100% orphan rejection)
      lint/
        test_no_auto_resolution.py                 # FR-004: aggregator.py has no winner-selection code
      integration/
        test_consistent_aggregation.py             # US1 happy path
        test_seeded_contradictions.py              # US2: conflict_detected=true, review task emitted
        test_missing_source_url.py                 # Edge: internal-only identifier preserved
        test_missing_publication_date.py           # Edge: undated memo handled with sentinel
        test_duplicate_claim_different_sources.py  # FR-008
      fixtures/
        consistent_aggregation.json
        seeded_contradictions.json
        missing_source_url.json
        missing_publication_date.json
        orphan_claim.json
        duplicate_claim_different_sources.json
```

**Structure Decision**: Single-project layout matching the Kata 1 convention
(see `specs/001-agentic-loop/plan.md` §Structure Decision) and the Kata 4
hub-and-spoke separation (`specs/004-subagent-isolation/plan.md` D-001).
`subagent.py` and `aggregator.py` live in **separate modules** so the
subagent-isolation discipline (Principle IV) is architecturally visible and the
AST lint (`test_no_auto_resolution.py`) has a single file to inspect for
forbidden winner-selection symbols. Runs written to `runs/<session-id>/`
(gitignored) match the Kata 1 and Kata 4 provenance layouts so cross-kata
tooling (e.g. dashboard summaries) sees a uniform shape.

## Architecture

```
┌────────────────────┐
│  Source Registry   │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│   Subagent Pool    │───────│    Coordinator     │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Provenance Aggr…│ │  Review Queue  │ │  Report Store  │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Source Registry` is the kata entry point; `Subagent Pool` owns the core control flow
for this kata's objective; `Coordinator` is the primary collaborator/policy reference;
`Provenance Aggregator`, `Review Queue`, and `Report Store` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: (a) concurrent subagent fan-out —
acceptance scenarios are stated sequentially; concurrency would obscure the
provenance audit without pedagogical value (same rationale as Kata 4 D-001);
(b) a vector-db-backed claim similarity index — the spec defines conflict as
textual contradiction on the canonical-claim-key, and semantic similarity
would reintroduce a probabilistic branch (Principle I violation); (c) retry
budgets on subagent failure — schema validation failures are terminal
(FR-002, FR-004), matching Kata 4's terminal-error discipline; (d) automatic
conflict resolution of any kind (FR-004, SC-002) — this is the kata's core
anti-pattern and its absence is the teaching point.
