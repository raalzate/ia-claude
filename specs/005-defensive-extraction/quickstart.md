# Kata 5 — Quickstart

## What you'll build

A Python extractor that turns an unstructured source document into a typed
`ExtractedRecord` via a forced Claude tool call — without fabricating a single
optional field. The model is pinned to the extraction tool with
`tool_choice={"type": "any"}`; optional fields are nullable unions so "I don't
know" is a first-class answer; enumerated fields ship with an `"other"` /
`"unclear"` escape option paired with a `details` capture so ambiguity is
audited rather than silently coerced.

## Prerequisites

- Python 3.11+
- `uv` or `pip`
- An Anthropic API key in `ANTHROPIC_API_KEY` — **only** needed when running
  against the live API; the default test run uses recorded fixtures.

## Install

```bash
# From repo root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # pyproject defines anthropic, pydantic v2, pytest, pytest-bdd
```

## Run the kata against recorded fixtures (default — no API key needed)

```bash
pytest tests/katas/005_defensive_extraction -v
```

You should see:
- the Gherkin `defensive_extraction.feature` scenarios pass,
- `tests/katas/005_defensive_extraction/unit/test_schema_lint.py` pass
  (proves no optional field is declared as a bare `str` — FR-004),
- `tests/katas/005_defensive_extraction/unit/test_tool_choice_forced.py` pass
  (proves every outgoing request carries `tool_choice.type == "any"` — FR-002),
- `tests/katas/005_defensive_extraction/unit/test_extra_forbid.py` pass
  (proves extra keys in the tool_use payload are rejected — FR-010),
- `tests/katas/005_defensive_extraction/unit/test_fabrication_rate.py` pass
  (proves zero fabrications across the labeled corpus — SC-001).

## Run the kata against the live API

```bash
LIVE_API=1 python -m katas.005_defensive_extraction.runner \
  --model claude-opus-4-7 \
  --source path/to/source.txt
```

Artifacts produced:
- stdout: the validated `ExtractedRecord` as pretty JSON
- `runs/<session-id>/extraction.jsonl` — one line with the extracted record,
  any `AmbiguityMarker`s emitted, and the `FabricationMetric` (if a labeled
  fixture was used).

## Fixture corpus (labeled, one case per Edge)

Each fixture directory contains `source.txt` + `expected.json` (a `null_map`
listing optional fields the labeler confirmed absent and an `escape_map`
listing enumerated fields that MUST route to the escape option). The
extraction output is audited against those labels — NOT against a
text-identity expected output.

| Fixture directory | Exercises | Assertion |
|-------------------|-----------|-----------|
| `well_formed/` | happy path | extracted record validates; zero nulls on required; no escape routing. |
| `missing_optional/` | optional absent from source | `null_map` fields come back `None` (not fabricated); `FabricationMetric.fabrication_count == 0`. |
| `ambiguous_enum/` | enum value not cleanly matching | `status` == `"unclear"` + non-empty `status_details`; AmbiguityMarker emitted. |
| `contradictory/` | two conflicting values in source | `status` == `"unclear"` + `status_details` captures both values. |
| `empty_source/` | source has no content | extraction fails schema validation on required fields; error surfaces field path. |
| `out_of_enum_value/` | enum value outside declared set | `status` == `"other"` + non-empty `status_details`. |

## Scenario → Spec map

| Scenario | User Story / FR / SC | Fixture |
|----------|----------------------|---------|
| Well-formed source returns a schema-valid record | US1-AS1/AS2/AS3, FR-001, FR-002, SC-002 | `well_formed` |
| Missing optional returns null (no fabrication) | US2-AS1/AS2, FR-004, FR-007, SC-004 | `missing_optional` |
| Batch audit: zero fabrications, null rate ≥ 99% | US2-AS3, SC-001, SC-004 | (all labeled) |
| Ambiguous value routes to escape enum with details | US3-AS1, FR-005 | `ambiguous_enum` |
| Contradictory statements route to escape enum | US3-AS2, FR-005, Edge: contradictory | `contradictory` |
| 100% ambiguous fixtures escape-routed | US3-AS3, SC-003 | (all ambiguous) |
| Empty source fails schema validation on required | Edge: empty, FR-006, FR-008 | `empty_source` |
| Out-of-enum value routes to 'other' | Edge: value outside set, FR-005, FR-010 | `out_of_enum_value` |
| Optional declared as bare `str` fails build | Anti-pattern gate, FR-004 | n/a — `test_schema_lint.py` |
| Outgoing request carries `tool_choice.type == "any"` | FR-002 | n/a — `test_tool_choice_forced.py` |
| Extra keys rejected | FR-010 | n/a — `test_extra_forbid.py` |

## Verify deterministic behavior

Inspect the run artifact:

```bash
jq -c '{subject, nickname, status, status_details, fabrication_count: .metric.fabrication_count}' \
  runs/<session-id>/extraction.jsonl
```

Every extraction records its `status` and (when escape-routed)
`status_details`. `fabrication_count` is `0` across labeled fixtures (SC-001).
No text-identity field leaks into the record.

## §Kata Completion Standards checklist (per Constitution v1.3.0)

- [ ] `spec.md`, `plan.md`, `tasks.md`, `.feature` file all exist — first two
      done here; `.feature` produced at `/iikit-04-testify`; `tasks.md` at
      `/iikit-05-tasks`.
- [ ] Acceptance scenarios cover stated objective AND stated anti-pattern —
      US1 (objective) + US2 (fabrication anti-pattern) + US3 (ambiguity
      anti-pattern).
- [ ] Automated evaluation uses signal-level assertions —
      `ExtractedRecord.model_validate(...)` outcome, `tool_choice` request
      shape, `extra="forbid"` outcome, `FabricationMetric` counter,
      `AmbiguityMarker` presence. No string matching over model prose.
- [ ] Anti-pattern test fails closed when regressed —
      `test_schema_lint.py` fails the build if an optional field is changed
      back to a bare `str` (FR-004).
- [ ] Assertion-integrity hashes in `.specify/context.json` match locked
      test set — produced at `/iikit-04-testify`.
- [ ] Per-kata `README.md` with objective / walkthrough / anti-pattern
      defense / run instructions / reflection — written at
      `/iikit-07-implement` (Principle VIII).
- [ ] Every non-trivial function (tool builder, schema lint, fabrication
      audit, ambiguity marker constructor) carries a *why* comment tied to
      FR-XXX/SC-XXX — enforced at implement review (Principle VIII).
- [ ] Reflection note records the observed failure mode the kata prevents —
      lives inside the README reflection section.

## Reflection prompt (answered at implement time)

- Which optional field was most tempting to fill with a plausible value, and
  what stopped the model from doing so — the `Optional[...] = None` annotation,
  the prompt wording, or both?
- Where in the schema would a non-nullable `str` sneak back in during
  maintenance (new field added without thinking), and how does
  `test_schema_lint.py` catch it before CI goes green?
- How does the `status_details` capture read on the `contradictory` fixture —
  does it preserve enough of the conflict for a human reviewer to act on?
