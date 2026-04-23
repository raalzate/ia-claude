# Implementation Plan: Defensive Structured Extraction with JSON Schemas

**Branch**: `005-defensive-extraction` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/005-defensive-extraction/spec.md`

## Summary

Build a Python kata module that extracts unstructured source documents into a
typed `ExtractedRecord` via a schema-bound Claude tool call with
`tool_choice={"type": "any"}`. The tool's `input_schema` is derived from a
pydantic v2 model whose optional fields are declared as nullable unions
(`Optional[str] = None`) and whose enumerated fields carry an escape value
(`"other"` / `"unclear"`) paired with a free-text `details` capture. A schema
lint test walks the pydantic model at test time and fails the build if any
optional field is declared as a non-nullable `str` (the kata's primary
anti-pattern). A fabrication-rate counter, computed against a labeled fixture
corpus, asserts zero hallucinated optional-field values (SC-001). Delivered
under Constitution v1.3.0 principles II (Schema-Enforced Boundaries, NN), VII
(Provenance & Self-Audit), and VIII (Mandatory Documentation, NN).

## Technical Context

**Language/Version**: Python 3.11+ (required for `typing.Literal`, PEP 604 `X | None`
syntax consumed by pydantic v2 field introspection used in the schema lint).
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — sole invocation path, required for
  `tool_choice={"type": "any"}` wiring that implements FR-002.
- `pydantic` v2 — single source of truth for `ExtractedRecord`,
  `SchemaDefinition`, `AmbiguityMarker`, and `FabricationMetric`. Used both to
  generate the tool `input_schema` (FR-001) and as the structural surface the
  schema lint walks (FR-004).
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify`; scenarios cover FR-002/FR-004/FR-005/FR-006/FR-007 and
  SC-001..SC-004.
**Storage**: Local filesystem only. Fixture corpus under
`tests/katas/005_defensive_extraction/fixtures/` — each fixture is a
`(source.txt, expected.json)` pair where `expected.json` encodes the
labeled null map and escape-enum map (NOT a text-identity expected output).
Run artifacts (if a live run is executed) written to
`runs/<session-id>/extraction.jsonl` (gitignored).
**Testing**: pytest + pytest-bdd for acceptance; plain pytest for the schema
lint and for the fabrication-rate audit. Shared `tests/katas/005_defensive_extraction/conftest.py`
exposes the fixture loader and the recorded-response client. Live API calls
are gated by `LIVE_API=1` (baseline shared with Kata 1 per `specs/001-agentic-loop/plan.md`).
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No deployment target.
**Project Type**: Single project — one kata module at
`katas/005_defensive_extraction/` with tests at
`tests/katas/005_defensive_extraction/`.
**Performance Goals**: Not latency-bound. Offline fixture run completes in
under 5 seconds locally (same budget as Kata 1).
**Constraints**:
- Every call to the Messages API from this kata MUST carry
  `tool_choice={"type": "any"}` — enforced by a pytest that asserts the
  outgoing request payload shape (FR-002).
- The pydantic `ExtractedRecord` model MUST NOT declare any optional field as
  a plain `str` — enforced by the schema-lint test (FR-004).
- The extractor MUST NOT emit any key outside the declared schema — enforced
  by `pydantic` `model_config = ConfigDict(extra="forbid")` on
  `ExtractedRecord` (FR-010).
- Zero fabricated optional-field values across the labeled corpus (SC-001);
  audited mechanically by `FabricationMetric` against the per-fixture null
  map.
**Scale/Scope**: One kata, ~250–400 LOC implementation + comparable test code;
one `README.md`; fixture corpus = six labeled items (well-formed,
missing-optional, ambiguous, contradictory, empty, out-of-enum) per the spec's
Edge Cases section.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Not load-bearing here (no multi-turn control flow) — but the branch on tool-call presence vs. absence still keys off the structured `content[0].type == "tool_use"` field, never on prose. |
| II. Schema-Enforced Boundaries (NN) | `ExtractedRecord` is a pydantic v2 model with `extra="forbid"` (FR-010); its JSON Schema is the `input_schema` passed to the extraction tool (FR-001). Required vs. optional fields are declared at the type level. Optional fields use nullable unions (FR-004). Enumerated fields include the escape value (FR-005). |
| III. Context Economy | Prompt construction follows stable-prefix (schema + instructions) / dynamic-suffix (source document) ordering so the schema portion of the prompt is cacheable across fixture runs. |
| IV. Subagent Isolation | Not applicable — this kata runs a single agent invocation per extraction. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` will run before any production code; `tasks.md` will cite `.feature` step IDs. |
| VI. Human-in-the-Loop | Validation failures (Edge: missing required field, empty source) MUST be surfaced to the caller with the offending field path (FR-008) rather than silently coerced — the reviewer is the escalation target. |
| VII. Provenance & Self-Audit | `FabricationMetric` is a per-run counter with a machine-readable trace of *which* optional fields were filled in without textual support. `AmbiguityMarker` pairs the escape enum with a `details` string preserving the observed raw value (FR-005), so ambiguity is auditable rather than hidden. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function (tool builder, schema lint, fabrication audit) will carry a *why* comment tying it to FR-XXX/SC-XXX. A `README.md` with objective, walkthrough, anti-pattern defense, run instructions, and reflection is written during `/iikit-07-implement`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/005-defensive-extraction/
  plan.md                      # this file
  research.md                  # Phase 0 output (decisions + Tessl discovery notes)
  data-model.md                # Phase 1 output (entity schemas)
  quickstart.md                # Phase 1 output (how to run the kata)
  contracts/                   # Phase 1 output (extraction JSON schemas)
    extraction-request.schema.json
    extracted-record.schema.json
    schema-definition.schema.json
    ambiguity-marker.schema.json
  tasks.md                     # (generated by /iikit-05-tasks)
  checklists/
    requirements.md            # (already present — /iikit-01 output)
  README.md                    # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  005_defensive_extraction/
    __init__.py
    models.py            # pydantic v2: ExtractedRecord, SchemaDefinition,
                         # AmbiguityMarker, FabricationMetric
    extractor.py         # build_extraction_tool() + run_extraction();
                         # forces tool_choice={"type": "any"} per FR-002
    client.py            # thin injectable Anthropic client wrapper
                         # (shared shape with Kata 1)
    audit.py             # fabricate-rate counter over a labeled fixture
                         # (SC-001)
    runner.py            # CLI: python -m katas.005_defensive_extraction.runner
    README.md            # written at /iikit-07

tests/
  katas/
    005_defensive_extraction/
      conftest.py        # fixture loader, recorded-response client,
                         # live-API toggle on LIVE_API=1
      features/          # Gherkin produced by /iikit-04-testify
        defensive_extraction.feature
      step_defs/
        test_defensive_extraction_steps.py
      unit/
        test_schema_lint.py        # FR-004 anti-pattern gate
        test_tool_choice_forced.py # FR-002 outgoing payload assertion
        test_extra_forbid.py       # FR-010 no extra keys
        test_fabrication_rate.py   # SC-001 audit against labeled corpus
      fixtures/
        well_formed/           source.txt, expected.json
        missing_optional/      source.txt, expected.json
        ambiguous_enum/        source.txt, expected.json
        contradictory/         source.txt, expected.json
        empty_source/          source.txt, expected.json
        out_of_enum_value/     source.txt, expected.json
```

**Structure Decision**: Single-project layout, sibling to Kata 1 per
`specs/001-agentic-loop/plan.md`. Each kata is a first-class package under
`katas/NNN_<slug>/`; tests mirror that structure. The fixture corpus is
labeled (each `expected.json` encodes the null map and escape-enum map, not a
text-identity expected output), which is the only way SC-001 / SC-003 / SC-004
can be asserted mechanically.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: retries, structured output via
JSON-mode (vs. tool use), multi-shot extraction, DB persistence, fuzzy schema
coercion. None are required by the spec; adding them would dilute the kata's
anti-pattern defense (FR-004, FR-007, FR-010).
