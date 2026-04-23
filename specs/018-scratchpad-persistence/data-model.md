# Phase 1 Data Model: Transactional Memory Preservation via Scratchpad

Pydantic v2 models at `katas/018_scratchpad_persistence/models.py`.
Source of truth is the structured tree; the `.md` file is a rendered view.

## Finding

One captured observation.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Stable within a scratchpad. |
| `timestamp` | `datetime` | UTC. |
| `category` | `Literal["architecture", "data", "bug", "decision", "question"]` | Routes to section. |
| `evidence` | `str` | What was observed. |
| `source_ref` | `str \| None` | File:line or URL where the evidence came from. |

## Scratchpad

| Field | Type | Notes |
|-------|------|-------|
| `pad_id` | `str` | UUID for this generation of the pad. |
| `version` | `int` | Monotonically increasing per write. |
| `prior_pad` | `str \| None` | Set on post-rotation pads. |
| `sections` | `dict[SectionName, list[Finding]]` | Section-name literals: `"map"`, `"findings"`, `"open_questions"`, `"decisions"`, `"conflicts"`. |
| `size_bytes` | `int` | Last rendered size. Validator asserts ≤ `MAX_SCRATCHPAD_BYTES`. |

**Invariants**
- Sections are fixed keys — unknown keys rejected.
- Adding a finding beyond `MAX_SCRATCHPAD_BYTES` triggers rotation BEFORE the
  write completes (D-004).

## ContextAnchor

| Field | Type | Notes |
|-------|------|-------|
| `anchor_id` | `str` | UUID. |
| `generated_at` | `datetime` | UTC. |
| `decisions_snapshot` | `list[Finding]` | Copied from `sections.decisions`. |
| `open_questions_snapshot` | `list[Finding]` | Copied from `sections.open_questions`. |
| `map_summary` | `str` (maxlen 400) | 2-line summary of `sections.map`. |
| `source_pad_id` | `str` | Scratchpad generation this anchor was built from. |

## RotationEvent

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | `str` | UUID. |
| `rotated_from` | `str` | Path of the now-archived pad. |
| `rotated_to` | `str` | Path of the fresh pad. |
| `size_at_rotation` | `int` | |
| `rotated_at` | `datetime` | UTC. |

## Relationships

```
Scratchpad (current)
  ├── Finding (N, grouped by section)
  ├── ContextAnchor (derived on compaction)
  └── RotationEvent (emitted when size cap hit)
        → new Scratchpad (prior_pad = previous pad_id)
```
