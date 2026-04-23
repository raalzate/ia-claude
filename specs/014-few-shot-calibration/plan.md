# Implementation Plan: Few-Shot Calibration for Edge Cases

**Branch**: `014-few-shot-calibration` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/014-few-shot-calibration/spec.md`

## Summary

Deliver an auditable Python kata that escapes zero-shot defaults on a highly
subjective/format-sensitive task by injecting 2–4 curated input/output example
pairs into the prompt and measuring the resulting consistency delta against the
same edge-case corpus. The kata ships: (a) pydantic v2 entities `ExamplePair`
and `ExampleSet` with a hard `2 <= len(pairs) <= 4` invariant (FR-006) and a
contradictory-pair validator that raises `ContradictoryExamplesError`
(FR-005, SC-003); (b) a `FewShotBuilder` that composes `system_instructions +
example_pairs + target_input` in *static-prefix-first* order so the fixed
section is Kata-10 prefix-cache-friendly (Constitution III); (c) an
`ExampleSetRegistry` that rotates between named sets and stamps the active set
id onto every run (FR-003, SC-004); (d) a measurement harness that runs the
same corpus zero-shot and few-shot, writes a `CalibrationReport`, and fails the
build if the few-shot run does not beat baseline by the declared reduction
target (SC-001, FR-004). Delivered under Constitution v1.3.0 — Principles
I (Determinism), II (Schema-Enforced Boundaries, NN), V (TDD, NN), VIII
(Mandatory Documentation, NN).

## Technical Context

**Language/Version**: Python 3.11+ (shared baseline with katas 001–013).
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — prompt submission + structured response
  consumption. Fixture-first; live mode gated by `LIVE_API=1`.
- `pydantic` v2 — schema enforcement for `ExamplePair`, `ExampleSet`,
  `FewShotPrompt`, `CalibrationReport` (Principle II). Length invariant and
  contradiction validator live on `ExampleSet` (FR-005, FR-006).
- `pytest` + `pytest-bdd` — BDD runner for `.feature` scenarios produced by
  `/iikit-04-testify` (Principle V / TDD).
- (Standard-library only beyond the above: `json`, `pathlib`, `uuid`, `hashlib`
  for stable example-pair ids.)
**Storage**: Local filesystem only. Each calibration cycle produces one
`CalibrationReport` JSON at `runs/<session-id>/calibration.json` and one
per-input JSONL trace at `runs/<session-id>/outputs.jsonl` (one line per
`(example_set_id, corpus_input)` pair for both zero-shot and few-shot arms).
No database; replayable from the two artifacts alone.
**Testing**: pytest + pytest-bdd for acceptance scenarios; plain pytest for
unit tests (validators, builder composition, metric computation). Recorded
fixtures (informal-measures corpus + calibrated / contradictory / over-long /
leakage-candidate example sets) drive the default offline suite. `LIVE_API=1`
opts into a real Messages API run over the same corpus for the "does this
actually calibrate the live model?" demonstration.
**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). No server deployment.
**Project Type**: Single project — kata module under
`katas/014_few_shot_calibration/`, tests under
`tests/katas/014_few_shot_calibration/`.
**Performance Goals**: Not latency-bound. Fixture-backed acceptance run
completes in under 5 seconds locally. Live `LIVE_API=1` calibration run over
the default 10-item informal-measures corpus completes in under 90 seconds on a
typical broadband link (corpus × 2 arms = 20 API calls).
**Constraints**:
- `ExampleSet` with `len(pairs) < 2 or len(pairs) > 4` MUST raise at
  construction — no silent truncation, no "we allowed 5 this time" (FR-006).
- Contradictory example sets MUST raise `ContradictoryExamplesError` *before*
  any API call is made (FR-005, SC-003).
- The few-shot run MUST NOT accept schema-invalid model output; schema-validity
  is part of the inconsistency metric (SC-002).
- Every run — zero-shot or few-shot — MUST stamp an `example_set_id` onto its
  `CalibrationReport`. Zero-shot runs use the reserved id `"zero_shot"`
  (FR-003, SC-004).
- Prompt composition MUST place the system instructions + example block as a
  contiguous *prefix* and the target input as the *suffix* to remain
  compatible with Kata 10's prefix-caching strategy (Constitution III,
  cross-reference to kata 010-prefix-caching).
- Zero-shot execution on a task the registry marks as "subjective /
  format-sensitive" MUST require an explicit `acknowledge_zero_shot=True`
  flag on the runner call (FR-007). Silent zero-shot on a calibratable task
  is the defended anti-pattern.
**Scale/Scope**: One kata, ~400–600 LOC implementation + comparable test code;
one README; fixture corpus: 10 informal-measure inputs × 2 arms, plus 4
distinct example sets (calibrated, alternate, contradictory, over-long) and 1
leakage-candidate flag fixture.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Calibration pass/fail keys off a **numeric** inconsistency delta against a declared threshold, not on text inspection of model output. Schema-validity is a typed boolean per output, not a "looks ok" judgement. |
| II. Schema-Enforced Boundaries (NN) | `ExamplePair`, `ExampleSet`, `FewShotPrompt`, `CalibrationReport` are all pydantic v2 models. `ExampleSet` carries the 2–4 invariant (FR-006) and the contradiction validator (FR-005). JSON Schema contracts in `contracts/` published for every one of them. |
| III. Context Economy | `FewShotBuilder` emits the system-instruction + example block as a stable prefix and the per-call target input as the dynamic suffix — aligning with Kata 10's prefix-cache strategy. Over-long example pairs are flagged by a size guard before they can push relevant content out of window. |
| IV. Subagent Isolation | Not applicable — single-agent calibration loop. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` produces `.feature` files + assertion-integrity hashes *before* production code. `tasks.md` (generated next by `/iikit-05-tasks`) references those scenarios. The contradictory-set fixture is a red test that MUST fail-closed before the validator is implemented. |
| VI. Human-in-the-Loop | FR-007 is the escalation clause: a zero-shot run on a subjective/format-sensitive task is halted unless the caller explicitly acknowledges the anti-pattern. |
| VII. Provenance & Self-Audit | Every run writes `example_set_id`, `corpus_id`, `model`, and per-input outputs to `calibration.json` / `outputs.jsonl`. The `CalibrationReport` pins both baseline and post-calibration rates plus the delta, so any recorded improvement is reproducible and auditable (SC-001, SC-004). |
| VIII. Mandatory Documentation (NN) | Every non-trivial function, validator, and schema will carry a *why* comment tied to the kata objective or to the anti-pattern it defends against. `README.md` (produced during `/iikit-07-implement`) will cover objective, walkthrough, anti-pattern defense, run instructions, and reflection. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/014-few-shot-calibration/
  plan.md              # this file
  research.md          # Phase 0 output (decisions + inconsistency-reduction target + Tessl discovery note)
  data-model.md        # Phase 1 output (ExamplePair, ExampleSet, FewShotPrompt, CalibrationReport)
  quickstart.md        # Phase 1 output (install, fixture run, LIVE_API run, scenario→spec map, Kata Completion checklist)
  contracts/           # Phase 1 output (JSON Schemas, $id kata-014)
    example-pair.schema.json
    example-set.schema.json
    calibration-report.schema.json
    consistency-metric.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  README.md            # Principle VIII deliverable (produced at /iikit-07)
```

### Source Code (repository root)

```text
katas/
  014_few_shot_calibration/
    __init__.py
    models.py           # pydantic v2: ExamplePair, ExampleSet, FewShotPrompt, CalibrationReport, ConsistencyMetric
    builder.py          # FewShotBuilder: composes system + examples (stable prefix) + target input (suffix)
    registry.py         # ExampleSetRegistry: named sets, rotation, active-set stamping (FR-003, SC-004)
    validators.py       # contradiction detector (FR-005), size guard for over-long examples, leakage-candidate flagger
    harness.py          # zero-shot vs. few-shot measurement harness; schema-validity + expected-value matching
    client.py           # thin injectable Anthropic client wrapper (fixture vs LIVE_API)
    runner.py           # CLI: python -m katas.014_few_shot_calibration.runner
    README.md           # kata narrative (written during /iikit-07)

tests/
  katas/
    014_few_shot_calibration/
      conftest.py       # fixture loader, corpus + example-set fixtures, calibration-report assertions
      features/         # Gherkin produced by /iikit-04-testify
        few_shot_calibration.feature
      step_defs/
        test_few_shot_calibration_steps.py
      unit/
        test_example_set_invariants.py     # FR-006: len 2..4; FR-005: contradiction raises
        test_builder_prefix_suffix_order.py # Constitution III + Kata 10 cross-ref
        test_registry_rotation.py          # FR-003, SC-004
        test_harness_metric.py             # SC-001, SC-002
        test_anti_pattern_flag.py          # FR-007: zero-shot without acknowledgement halts
      fixtures/
        corpus_informal_measures.json      # "a pinch" / "a handful" / "a splash" × 10
        example_set_calibrated.json        # the canonical 3-pair set
        example_set_alternate.json         # rotation target (US3, SC-004)
        example_set_contradictory.json     # MUST fail-closed (FR-005, SC-003)
        example_set_overlong.json          # size-guard fixture (edge case #4)
        example_pair_leakage_candidate.json # flagged, not fatal (edge case #2)
```

**Structure Decision**: Same single-project layout as Kata 001 and prior
katas — `katas/014_few_shot_calibration/` with mirrored tests under
`tests/katas/014_few_shot_calibration/`. Runs are written to
`runs/<session-id>/` (gitignored). This keeps every kata independently
buildable and testable, matching the FDD cadence in Constitution §Development
Workflow.

## Architecture

```
┌────────────────────┐
│ Calibration Runner │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  FewShot Builder   │───────│  Example Registry  │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│  Messages API  │ │   Trial Log    │ │  Report Store  │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Calibration Runner` is the kata entry point; `FewShot Builder` owns the core control flow
for this kata's objective; `Example Registry` is the primary collaborator/policy reference;
`Messages API`, `Trial Log`, and `Report Store` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally omitted: training / fine-tuning, dynamic example
*selection* (retrieval-augmented few-shot), automated example generation,
multi-model cross-checks. These belong to later katas (softmax-mitigation,
self-correction, adaptive-investigation) and would dilute the one lesson this
kata teaches: **hand-curated 2–4 example pairs, placed as a stable prefix,
measurably beat zero-shot on subjective tasks**.
