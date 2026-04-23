# Kata 11 — Quickstart

## What you'll build

A `PromptBuilder` that emits three layouts (edge-placed, mid-buried,
edge-placed + proactive-compaction) for the SAME critical rule set + filler
corpus. A compliance harness runs N trials per layout and reports a rule-
obedience rate. A `CompactionTrigger` fires at 55% context usage and re-anchors
every critical rule at its declared edge.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/011_softmax_mitigation -v
```

Fixture-mode compliance uses recorded responses so the test is deterministic.
Asserts:
- `edge_placed` obedience ≥ declared target.
- `mid_buried` obedience ≤ `edge_placed` − declared delta.
- `edge_placed_with_compaction` obedience ≥ `edge_placed` across long sessions.
- Compaction event fires BEFORE usage exceeds 60%.
- Post-compaction prompt contains every `CriticalRule.id` listed in the event.

## Run a live A/B/C compliance sweep

```bash
LIVE_API=1 python -m katas.011_softmax_mitigation.sweep --trials 20
```

Writes `runs/<session-id>/compliance.jsonl` with one `ComplianceRecord` per
trial per layout, and prints a summary table.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Edge-placed rule obeyed | US1, SC-001 | `edge_placed_run.json` |
| Mid-buried rule violated more | US2, SC-002 | `mid_buried_run.json` |
| Compaction re-anchors rules | US3, SC-003, SC-004 | `compaction_run.json` |
| Rule longer than edge budget | Edge #1 | `oversized_rule.json` |
| Multi-rule edge competition | Edge #3 | `multi_rule_contention.json` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Anti-pattern (mid burying) defended by A/B comparison harness.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- How did compliance change when TWO critical rules competed for the same edge
  region? Did the deterministic priority break the tie the way you expected?
- Which critical rule from this repo's own Constitution would you place at
  edges first, and why?
