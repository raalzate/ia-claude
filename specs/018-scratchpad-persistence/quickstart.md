# Kata 18 — Quickstart

## What you'll build

An `investigation-scratchpad.md` with a fixed section schema (map · findings ·
open_questions · decisions · conflicts), an append-only `ScratchpadWriter` API
with flock-serialized writes, and a `ContextAnchor` that seeds a post-compact
session so the agent resumes without rediscovering the same facts.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/018_scratchpad_persistence -v
```

Asserts:
- Fresh pad loads cleanly on session start.
- Each `add_finding` round-trips: write → read → equivalent (D-006).
- Compaction at 55% produces a `ContextAnchor`; post-resume probe answers
  without re-running the investigation (SC-001 rediscovery-rate = 0).
- Size cap exceeded → `RotationEvent` fires; new pad's `prior_pad` points to
  rotated file; cap never exceeded (SC-004).
- Corrupted pad loads → `ScratchpadSchemaError` (fail loud).
- Concurrent writers serialize via flock; no torn writes.

## Inspect a live investigation

```bash
LIVE_API=1 python -m katas.018_scratchpad_persistence.investigate \
  --directive "Map the auth module and list its open questions" \
  --pad runs/session-$(uuidgen)/investigation-scratchpad.md
```

Watch the pad grow as findings come in; force compaction:

```bash
python -m katas.018_scratchpad_persistence.compact \
  --pad runs/session-*/investigation-scratchpad.md
```

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Findings persist + round-trip | US1 | `running_investigation/` |
| Compact-resume avoids rediscovery | US2, SC-001 | `pre_compact/`, `post_compact/` |
| Structured sections, not prose | US3, SC-002 | parse round-trip |
| Unbounded growth triggers rotation | Edge #1 | `oversize_pad/` |
| Conflicting findings routed to `## Conflicts` | Edge #2 | `conflicting_findings/` |
| Missing pad at start → empty skeleton | Edge #3 | `missing_pad/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Ephemeral-only-memory anti-pattern defended by compact-resume fixture.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- What was the last thing that got lost across a compaction before you had the
  pad? How would its absence have surfaced?
- Where did the `## Conflicts` section end up being most useful?
