# Phase 0 Research: Data Provenance Preservation

## Decisions

### D-001 — Provenance fields required on every emitted claim

- **Decision**: `Claim` pydantic model has `claim` + `source_name` (required
  non-empty strings), `source_url` (nullable — may be a `file://` path or an
  `internal://manual-id` identifier), `publication_date` (nullable when
  unknown). Missing required fields → `ValidationError` pre-emission.
- **Rationale**: FR-001 + SC-001. Orphan claims are the core failure mode.
- **Alternatives**: All fields required including date — rejected (some
  internal manuals legitimately lack one). Strict URL — rejected (internal
  manuals use custom scheme).

### D-002 — Canonical claim key via sha256 of normalized text

- **Decision**: `canonical_key(claim_text)` = sha256 of lowercased, whitespace-
  collapsed, stopword-preserved claim text. Duplicate canonical keys from
  different sources are grouped. Disagreement on numeric content (detected
  via numeric-token extraction per pair) raises `conflict_detected=true`.
- **Rationale**: Robust to formatting drift; deterministic; avoids an
  embedding dependency.
- **Alternatives**: Sentence embeddings — rejected (adds a heavy dep for
  marginal benefit; harder to explain in a kata).

### D-003 — Conflict routing never auto-resolves

- **Decision**: When `ProvenanceAggregator` detects disagreeing claims, both
  (all) claims remain in a `ConflictSet` with `conflict_detected=true`; a
  `ReviewTask` is emitted. The aggregator never picks one as "canonical".
- **Rationale**: FR-004 + SC-002 + Principle VII (NN-aligned).

### D-004 — Subagent isolation via typed payload

- **Decision**: Each subagent returns a `SubagentClaimsPayload` validated
  against `subagent-claims-payload.schema.json`. The coordinator aggregates
  solely from these payloads; it does not read subagent private history.
  Reuses the hub-and-spoke pattern from Kata 4.
- **Rationale**: Principle IV coherence; forces provenance to survive the
  isolation boundary (it's part of the typed contract).

### D-005 — Orphan-claim lint as post-aggregation gate

- **Decision**: `OrphanClaimLint` runs after aggregation; any claim missing
  a required provenance field → `OrphanClaimError` and the run fails closed.
  SC-004.
- **Rationale**: Belt-and-braces: schema already enforces, but a post-step
  check catches programmer errors that might inject claims outside the
  schema-validated path.

### D-006 — Cross-source duplicate handling

- **Decision**: Identical claims from multiple sources are NOT deduped;
  `AggregationReport` records them as `supporting_sources` list. Diverging
  claims are the only "conflict" case.
- **Rationale**: Multi-source corroboration is a feature, not noise.

## Tessl Tiles

`tessl search provenance` — no applicable tile. None installed.

## Unknowns

None.
