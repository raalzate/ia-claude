# Kata 14 — Quickstart

## What you'll build

A `FewShotBuilder` that composes a prompt from a curated `ExampleSet` (2–4
pairs) for subjective-format tasks (e.g. "a pinch of salt" → structured
amount). A calibration harness compares zero-shot vs. few-shot on an edge-case
corpus and emits a `CalibrationReport` proving inconsistency dropped by the
declared target.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/014_few_shot_calibration -v
```

Asserts:
- `ExampleSet` accepts 2–4 pairs; rejects 0, 1, 5+ at construction.
- Contradictory set raises `ContradictoryExamplesError`.
- Oversized example is flagged (size guard).
- Fixture-mode calibration report shows few-shot < zero-shot inconsistency by
  declared delta.

## Run a live calibration

```bash
LIVE_API=1 python -m katas.014_few_shot_calibration.calibrate \
  --task informal_measures \
  --corpus tests/katas/014_few_shot_calibration/fixtures/informal_measures_corpus.json \
  --set-id v1_pinch_handful_splash
```

Emits:
- `runs/<session-id>/trials.jsonl` — one `ConsistencyMetric` per trial
- `runs/<session-id>/report.json` — the `CalibrationReport`

## Rotate example sets

```bash
for set_id in v1_pinch_handful_splash v2_refined v3_minimal; do
  LIVE_API=1 python -m katas.014_few_shot_calibration.calibrate \
    --task informal_measures --set-id $set_id
done
```

Active set is recorded per run (FR-003, SC-004).

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Few-shot beats zero-shot | US1, SC-001 | `informal_measures_corpus.json` |
| Zero-shot baseline demo | US2 | same corpus, `--set-id none` |
| Example-set quality sensitivity | US3 | `good_set/`, `poor_set/` |
| Contradictory set rejected | Edge #1, FR-005 | `contradictory_set/` |
| Oversized example flagged | Edge #4 | `oversized_example/` |

## Fixture-id mapping

The `set_id` values used in the US3 Scenario Outline (`calibrated_primary`,
`calibrated_alternate`) map to the on-disk fixtures under
`tests/katas/014_few_shot_calibration/fixtures/` as follows:

| `set_id` (scenario outline) | Fixture file |
|-----------------------------|--------------|
| `calibrated_primary` | `example_set_calibrated.json` |
| `calibrated_alternate` | `example_set_alternate.json` |
| `zero_shot` (reserved control) | — (no fixture; synthesized by runner) |
| `contradictory` | `example_set_contradictory.json` |
| `overlong` | `example_set_overlong.json` |
| `missing_coverage` | `example_set_missing_coverage.json` |

The `ExampleSetRegistry` loader wires each `set_id` above to its fixture path
at test-session startup; any scenario referencing a `set_id` not in this table
raises `UnknownExampleSetError` before any API call.

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Anti-pattern (zero-shot on subjective tasks) defended by baseline comparison.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- Which edge case improved the MOST with calibration? Which didn't improve?
- Did the example rotation reveal any hidden leakage from one set into
  another? How would you detect that automatically?
