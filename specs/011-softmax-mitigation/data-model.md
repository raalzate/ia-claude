# Phase 1 Data Model: Softmax Dilution Mitigation

All entities below are implemented as pydantic v2 models at
`katas/011_softmax_mitigation/models.py`. Validation runs on construction; any
invalid payload raises `pydantic.ValidationError` and the run halts. JSON
Schema exports live under `specs/011-softmax-mitigation/contracts/` with
`$id` prefix `https://ia-claude.local/schemas/kata-011/`.

## CriticalRule

A hard, non-negotiable constraint the model must obey.

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` (slug, `^[a-z][a-z0-9_-]{0,63}$`) | Stable rule identifier. Used in logs and compliance records. |
| `content` | `str` (min length 1) | Verbatim rule text. Placed at both edges *unchanged* (FR-001, FR-003). |
| `length_tokens` | `int` (≥ 1) | Token count of `content` under the kata's declared tokenizer. Computed at construction — not trusted from input. |
| `priority` | `int` (≥ 0) | Lower wins; ties broken by input order (D-005). |
| `compliance_target_pct` | `float` in `[0, 100]` | Per-rule override of the layout-level 95% target (D-003). Default = inherited layout target. |
| `compliance_probe_schema` | `dict[str, Any]` (JSON Schema) | Describes the structured JSON the model is asked to emit so scoring is signal-driven (D-006). |

**Invariants**
- `content` is immutable after construction — mutation would let compaction
  silently paraphrase a rule (spec.md edge case "compaction collapses
  critical rule").
- `length_tokens` is recomputed by the validator; any caller-supplied value
  that disagrees with the tokenizer raises `ValidationError`.

**Why it exists**: FR-001, FR-003 — the rule *must* be placed verbatim; no
other entity in the system is allowed to paraphrase it.

## EdgeRegion

A bounded portion of the prompt at either edge.

| Field | Type | Notes |
|-------|------|-------|
| `position` | `Literal["primacy", "latency"]` | Top vs bottom of the prompt. |
| `budget_tokens` | `int` (≥ 1) | Hard cap on tokens placed in this region. |
| `placed_rule_ids` | `list[str]` | Ordered list of `CriticalRule.id`s currently inside this region. |
| `deferred_rule_ids` | `list[str]` | Rules that failed to fit under the budget (surfaced, never dropped silently — spec.md multi-rule edge case). |

**Invariants**
- `sum(rule.length_tokens for rule in placed) ≤ budget_tokens` — enforced by
  validator, never by hope.
- The same rule id appears in at most one of `placed_rule_ids` /
  `deferred_rule_ids` per region.

**Why it exists**: FR-001, FR-005 — the region is where the reject-content
gate enforces its invariant. Content that would push a placed rule over the
budget raises `EdgePlacementViolation` at build time.

## PromptLayout

One rendered prompt plus the structural metadata needed to audit it.

| Field | Type | Notes |
|-------|------|-------|
| `label` | `Literal["edge_placed", "mid_buried", "edge_placed_with_compaction"]` | Which layout family this instance is. |
| `rendered_prompt` | `str` | The exact string passed to `messages.create(...)`. |
| `primacy_region` | `EdgeRegion` | Always `position="primacy"`. |
| `latency_region` | `EdgeRegion` | Always `position="latency"`. Empty for `mid_buried`. |
| `mid_body_tokens` | `int` (≥ 0) | Token count of the filler corpus between the edges. |
| `total_tokens` | `int` (≥ 1) | Full prompt token count (edges + body). |
| `context_window_tokens` | `int` (≥ `total_tokens`) | Model's declared window; used by the compaction trigger. |
| `usage_fraction` | `float` in `[0, 1]` | `total_tokens / context_window_tokens`. Populated at build time for the trigger to read. |
| `compliance_target_pct` | `float` in `[0, 100]` | Declared target for this layout (default 95%, D-003). |
| `min_delta_pct` | `float` in `[0, 100]` | Declared minimum compliance drop versus the edge-placed comparator. Populated on the `mid_buried` layout only (default 20 pp, D-003). |
| `allow_anti_pattern` | `bool` | MUST be True iff `label == "mid_buried"` (FR-006). |
| `rendered_at` | `datetime` (UTC) | Populated at construction. |

**State transitions**
1. `PromptBuilder` constructs a layout from a `list[CriticalRule]` + filler
   corpus + context-window size.
2. If construction would leave a critical rule out of its edge region on the
   `edge_placed` / `edge_placed_with_compaction` layouts, the builder raises
   `EdgePlacementViolation` (FR-005) — the layout instance is never
   constructed in a violating state.
3. If the layout's `label == "edge_placed_with_compaction"` and a
   `CompactionEvent` fires during a session, a fresh `PromptLayout` is
   rendered with every rule re-anchored verbatim at both edges (FR-003).

**Invariants**
- `mid_buried` layouts MUST have `primacy_region.placed_rule_ids == []` AND
  `latency_region.placed_rule_ids == []` — anti-pattern cannot coexist with
  edge anchoring.
- Every other layout MUST have every declared rule's id listed in BOTH
  `primacy_region.placed_rule_ids` AND `latency_region.placed_rule_ids`.

**Why it exists**: FR-001, FR-003, FR-005, FR-006, SC-001, SC-002, SC-004 —
the layout is the auditable artifact that post-run tooling inspects to verify
every edge invariant held.

## CompactionEvent

A record of a proactive compaction.

| Field | Type | Notes |
|-------|------|-------|
| `event_id` | `str` (UUID4) | Unique event identifier. |
| `session_id` | `str` | Parent session. |
| `fired_at_usage_fraction` | `float` in `[0.55, 0.60]` | Trigger point (D-004). Values outside this band raise — either fired too early or too late. |
| `pre_compaction_total_tokens` | `int` | Pre-compaction prompt size. |
| `post_compaction_total_tokens` | `int` | Post-compaction prompt size. |
| `collapsed_turn_count` | `int` (≥ 1) | How many turns were summarised. |
| `summary_text` | `str` | The generated summary (stored for audit — loop logic does not read it). |
| `rules_preserved` | `list[str]` | Rule ids that survived, verbatim, at both edges. |
| `rules_missing_after` | `list[str]` | Rule ids that failed re-anchoring. MUST be `[]` — any non-empty value is SC-004's fail-closed path. |
| `emitted_at` | `datetime` (UTC) | |

**Invariants**
- `0.55 ≤ fired_at_usage_fraction < 0.60` is enforced by validator — FR-002
  and SC-003 together require both the floor and the ceiling.
- `post_compaction_total_tokens < pre_compaction_total_tokens` — compaction
  that doesn't reduce is a bug.
- `rules_missing_after == []` — non-empty fails SC-004; the run aborts rather
  than proceeding with a silently-degraded prompt (spec.md edge case
  "compaction collapses critical rule" + "anti-pattern slips back in").

**Why it exists**: FR-002, FR-003, FR-004, SC-003, SC-004 — this is the
audit-trail object for the compaction half of the kata.

## ComplianceRecord

One trial in the compliance harness — the atomic row of the JSONL log.

| Field | Type | Notes |
|-------|------|-------|
| `trial_id` | `str` (UUID4) | |
| `session_id` | `str` | Parent sweep session. |
| `layout_label` | `Literal["edge_placed", "mid_buried", "edge_placed_with_compaction"]` | Which layout this trial exercised. |
| `rule_id` | `str` | Which `CriticalRule` was probed. |
| `model` | `str` | Claude model id used. |
| `outcome` | `Literal["obeyed", "violated", "undetermined"]` | Signal-driven scoring (D-006); `undetermined` surfaces rather than coerces. |
| `probe_payload` | `dict[str, Any] \| None` | The structured JSON the model emitted against `rule.compliance_probe_schema`. Null iff `outcome == "undetermined"`. |
| `prompt_hash` | `str` (sha256, hex) | Hash of the exact `PromptLayout.rendered_prompt`. Ties the trial to its prompt for replay. |
| `latency_ms` | `int` (≥ 0) | Measured round-trip. Audit-only — not asserted. |
| `recorded_at` | `datetime` (UTC) | |

**Invariants**
- `outcome == "obeyed"` MUST have a non-null `probe_payload` that validates
  against the probed rule's `compliance_probe_schema` — a record cannot
  *claim* obedience without the structured evidence.
- `prompt_hash` is computed once at record construction and cannot be
  overwritten — guarantees the trial references the exact prompt that was
  sent.

**Why it exists**: FR-007, SC-001, SC-002 — the compliance table is the
aggregation target. The per-record schema is what keeps aggregation honest.

## Relationships

```
Session (kata-011 run)
  ├── layouts:       [PromptLayout]        (one per label rendered)
  │     ├── primacy_region: EdgeRegion
  │     │     └── placed_rule_ids: [CriticalRule.id]
  │     └── latency_region: EdgeRegion
  │           └── placed_rule_ids: [CriticalRule.id]
  ├── compaction_events: [CompactionEvent]    (one per compaction trigger fire)
  └── compliance_records: [ComplianceRecord]  (one per (layout × rule × trial))
```

## Exceptions (not entities, but part of the model boundary)

| Exception | Trigger | FR / SC |
|-----------|---------|---------|
| `EdgePlacementViolation` | Adding non-critical content would push a `CriticalRule` out of its `EdgeRegion`. | FR-005 |
| `AntiPatternNotAuthorized` | Caller asked for `mid_buried` without `allow_anti_pattern=True`. | FR-006 |
| `CompactionOverdue` | `CompactionTrigger.should_fire(usage)` returned False and `usage > 0.60`. | FR-002, SC-003 |
| `RuleMissingAfterCompaction` | `CompactionEvent` constructed with non-empty `rules_missing_after`. | FR-003, SC-004 |

## What is deliberately NOT modeled

- A general-purpose `PromptComposer` shared with kata 010 — revisit after
  kata 010 implement lands (plan.md Complexity Tracking).
- Async batch sweeps for the compliance harness — deferred until the default
  N × 3 sweep outgrows live rate limits (plan.md Complexity Tracking).
- Per-rule priority classes ("blocking" vs "advisory") — the kata ships one
  class (hard guardrail) by design; advisory rules would dilute the
  Principle III lesson.
