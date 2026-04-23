# Phase 0 Research: Structured Human Handoff Protocol

## Decisions

### D-001 — Tool-bound escalation (not prose signal)

- **Decision**: The only escalation surface is a `escalate_to_human` tool
  registered with the Messages API; its `input_schema` is the full
  `HandoffPayload` pydantic schema. The model cannot "opt out" — if the escalation
  condition fires and the tool isn't invoked, the pipeline raises.
- **Rationale**: Principle II (NN) + anti-pattern defense. Prose-only handoffs
  are what the kata defeats; tool binding is the only mechanism the SDK
  validates.
- **Alternatives**:
  - *System-prompt instruction only.* Rejected: non-deterministic.
  - *Prose + post-hoc parser.* Rejected: Principle I violation.

### D-002 — Session suspension via a hard-failing client wrapper

- **Decision**: Wrap `anthropic.Anthropic().messages.create` in a
  `SuspensionAwareClient` that tracks a flag `session_suspended: bool`. After
  `escalate_to_human` is observed, every further call raises
  `SessionSuspended`. FR-001 says 0 bytes of additional conversational content;
  this operationalizes it.
- **Rationale**: Clean failure mode is preferable to a "don't call me" comment.
- **Alternatives**: Ignore-and-discard the subsequent calls silently —
  rejected (Principle I: fail loud).

### D-003 — OperatorQueue as JSONL under `runs/handoffs/`

- **Decision**: One file per `escalation_id` at
  `runs/handoffs/<escalation_id>.json`; plus an append-only index
  `runs/handoffs/index.jsonl` of `{escalation_id, created_at, severity, status}`.
- **Rationale**: Traceable by `escalation_id` (SC-004), human-queryable without
  a database, survives crashes.
- **Alternatives**: SQLite (overkill); streaming to a webhook (out of
  workshop scope).

### D-004 — Schema evolution with required-field addition

- **Decision**: Adding `severity` as required bumps the handoff schema minor
  version. Old payloads (without `severity`) are rejected by the validator
  (FR-010, SC-001). The test explicitly asserts legacy-payload rejection.
- **Rationale**: Schema evolution must be observable; silent optional-add
  hides compatibility drift.

### D-005 — Anti-pattern surfaces (prose-only handoff)

- **Decision**: The test fixture registers an additional tool
  `send_human_a_note` whose input is free text. The validator blocks that
  tool from being used as an escalation surface — only `escalate_to_human`
  counts. The kata fails if the validator accepts the prose-only path.
- **Rationale**: Anti-pattern defense must be structural, not advisory.

### D-006 — Convergent shape across escalation sources

- **Decision**: `HandoffPayload` is the union type consumed by katas 2
  (PreToolUse breach) and 6 (retry-budget exhausted). Both upstream katas
  construct a `HandoffPayload` at their escalation point; no translator layer
  is needed.
- **Rationale**: FDD cross-kata coherence. Avoids one-off shapes per upstream.

## Tessl Tiles

`tessl search handoff` / `tessl search escalation` — no applicable tiles.
None installed.

## Unknowns

None. All spec placeholders resolved.
