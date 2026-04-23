# Phase 1 Data Model: Few-Shot Calibration for Edge Cases

All entities implemented as pydantic v2 models at
`katas/014_few_shot_calibration/models.py`. Construction-time validation is the
floor Principle II (NN) demands.

## ExamplePair

One input/output calibration pair.

| Field | Type | Notes |
|-------|------|-------|
| `input` | `str` | Free-text input the edge case covers. |
| `output` | `dict[str, Any]` | Structured expected output — MUST validate against the task's output schema. |
| `notes` | `str \| None` | Optional rationale for curriculum purposes. |

## ExampleSet

Ordered collection of 2–4 pairs. Pydantic validator enforces `2 ≤ len ≤ 4`.

| Field | Type | Notes |
|-------|------|-------|
| `set_id` | `str` | Stable identifier; logged per run (FR-003, SC-004). |
| `description` | `str` | What the set calibrates for. |
| `pairs` | `list[ExamplePair]` | 2–4 entries. |

**Invariants**
- `ContradictoryExamplesError` is raised when any two pairs share an input
  prefix but disagree on a same-field output value (FR-005).
- Detection uses a canonical-normalization function (lowercasing, whitespace
  collapse) declared in research.md.

## FewShotPrompt

Composed prompt the SDK receives.

| Field | Type | Notes |
|-------|------|-------|
| `system_instructions` | `str` | Task framing (static — Kata 10 compatible prefix). |
| `examples_block` | `str` | Rendered from the active `ExampleSet`. Static with respect to a given set. |
| `target_input` | `str` | The edge-case input to classify. Dynamic — belongs at the suffix. |

## CalibrationReport

Output of the measurement harness.

| Field | Type | Notes |
|-------|------|-------|
| `task_id` | `str` | Calibration task name. |
| `set_id` | `str \| None` | The active `ExampleSet.set_id`; null for zero-shot control. |
| `corpus_size` | `int` | Number of edge-case inputs used. |
| `inconsistency_rate` | `float` (0..1) | Failures + schema violations / corpus_size. |
| `schema_violation_rate` | `float` (0..1) | Subset of inconsistency: strict schema failures. |
| `timestamp` | `datetime` | UTC. |

## ConsistencyMetric

Per-trial record; multiple accumulate into a CalibrationReport.

| Field | Type | Notes |
|-------|------|-------|
| `trial_id` | `str` | UUID4. |
| `mode` | `Literal["zero_shot", "few_shot"]` | Which control branch. |
| `set_id` | `str \| None` | Active ExampleSet id on the trial; null for zero-shot. |
| `input_text` | `str` | The tested edge-case input. |
| `model_output` | `dict \| None` | Parsed model output; null on schema failure. |
| `schema_valid` | `bool` | `True` iff output validates against the task schema. |
| `matches_expected` | `bool \| None` | Set iff there is a labeled expected output for this input. |

## ExampleSetRegistry (in-memory catalog, not a schema)

A `dict[set_id, ExampleSet]` used to rotate through sets during evaluation.
Active set per run is written to the event log so SC-004 is traceable.

## Relationships

```
ExampleSetRegistry
  └── ExampleSet (1..N)
         └── ExamplePair (2..4)

Trial Run
  ├── FewShotPrompt (one per trial, built from the active ExampleSet)
  └── ConsistencyMetric (one per trial)
        → rolls up into CalibrationReport
```
