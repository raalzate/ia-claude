# Phase 1 Data Model: Data Provenance Preservation

Pydantic v2 models at `katas/020_data_provenance/models.py`.

## Source

A registered corpus document.

| Field | Type | Notes |
|-------|------|-------|
| `source_id` | `str` | Short machine identifier. |
| `name` | `str` | Human-readable ("2025 Employee Handbook v3"). |
| `url` | `str \| None` | `https://…`, `file://…`, or `internal://source-id`. |
| `publication_date` | `date \| None` | Nullable when unknown. |
| `version` | `str \| None` | |

## Claim

The emitted fact unit — provenance is schema-required.

| Field | Type | Notes |
|-------|------|-------|
| `claim_id` | `str` | UUID per emission. |
| `claim` | `str` | The factual statement; non-empty. |
| `source_name` | `str` | Mirrors Source.name — required non-empty. |
| `source_url` | `str \| None` | Mirrors Source.url; nullable. |
| `publication_date` | `date \| None` | Mirrors Source.publication_date. |
| `canonical_key` | `str` | sha256 over normalized claim text (research D-002). |
| `extracted_by` | `str` | Subagent id. |

**Invariants**
- `source_name` required non-empty — `source_url` may be null to permit
  internal manuals, but `source_name` never.
- `canonical_key` computed on construction — immutable.

## SubagentClaimsPayload

What each subagent returns.

| Field | Type | Notes |
|-------|------|-------|
| `subagent_id` | `str` | |
| `source_ids` | `list[str]` | Which Sources the subagent read. |
| `claims` | `list[Claim]` | At least one; may be empty only if the subagent explicitly notes "no claims extracted". |
| `notes` | `str \| None` | Free text; coordinator ignores for aggregation. |

## AggregationReport

Top-level result of a run.

| Field | Type | Notes |
|-------|------|-------|
| `run_id` | `str` | UUID. |
| `claims` | `list[ClaimGroup]` | See below. |
| `conflicts` | `list[ConflictSet]` | |
| `orphan_claims` | `list[str]` | `claim_id`s rejected by OrphanClaimLint (expected length 0 on clean runs — SC-004). |
| `aggregated_at` | `datetime` | UTC. |

## ClaimGroup

| Field | Type | Notes |
|-------|------|-------|
| `canonical_key` | `str` | |
| `supporting_sources` | `list[Claim]` | Distinct sources whose claims share the canonical key and do not disagree numerically. |

## ConflictSet

| Field | Type | Notes |
|-------|------|-------|
| `canonical_key` | `str` | |
| `conflict_detected` | `Literal[True]` | Always true for entries in this list. |
| `claims` | `list[Claim]` | ≥ 2 contradictory claims. |
| `numeric_divergence` | `list[dict]` | Per-numeric-token divergence audit, optional. |

## ReviewTask

Human-in-the-loop escalation for conflict resolution.

| Field | Type | Notes |
|-------|------|-------|
| `task_id` | `str` | UUID. |
| `conflict_set_key` | `str` | Matches `ConflictSet.canonical_key`. |
| `status` | `Literal["pending", "resolved"]` | |
| `resolution_note` | `str \| None` | |

## Relationships

```
Source (registered) ──┐
                      ├── SubagentClaimsPayload (per subagent)
                      │        └── Claim (provenance-required)
                      │
Coordinator ─────────► AggregationReport
                             ├── ClaimGroup (corroborated)
                             ├── ConflictSet (disagreement)
                             │       └── ReviewTask
                             └── orphan_claims (must be empty)
```
