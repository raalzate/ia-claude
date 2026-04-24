# Feature Specification: Data Provenance Preservation

**Feature Branch**: `020-data-provenance`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 20 — Strictly maintain the mapping between factual claims and their original sources after executing massive aggregations across subagent-processed corporate manuals. Reject amalgamated prose summaries; reject silent conflict resolution; route conflicts to humans."

## Clarifications

### 2026-04-24 (phase-06 analyze)

- **SC-003 (recall threshold)**: Conflict detection recall on the seeded conflict set MUST be `100%` — every planted contradiction MUST surface as a `conflict_detected=true` record (consistent with SC-002's no-silent-drops discipline). Missing even one seeded contradiction is a SC-003 failure.
- **FR-003 (conflict-detection scope)**: FR-003 covers numeric-token divergence within a `canonical_key` group (the aggregator's supported detection path at T045). Categorical-contradiction detection (e.g., two sources asserting different policy owners) is out of scope for this kata and is deferred to a later kata / issue. RESOLVED (2026-04-24) — `/iikit-04-testify` re-run pinned the numeric-only scope with TS-021 (categorical-only disagreements produce zero ConflictSets and increment `deferred_categorical_conflicts`) and TS-022 (numeric-token divergence across `canonical_key` groups reliably raises a conflict). Assertion-integrity hash refreshed.

## User Stories *(mandatory)*

### User Story 1 - Provenance-Preserving Aggregation (Priority: P1)

A practitioner submits multiple corporate manuals to a fleet of subagents and receives a structured JSON list where every factual claim is tagged with its originating `source_url`, `source_name`, and `publication_date`. No claim is ever stripped of its provenance or fused into an anonymous summary paragraph.

**Why this priority**: This is the core auditability promise of Kata 20. Without preserved provenance, every downstream decision rests on unverifiable assertions — exactly the hallucination surface the workshop is teaching practitioners to eliminate (Constitution VII).

**Independent Test**: Can be fully tested by passing two distinct manuals to two subagents, requesting claim extraction, and verifying each emitted claim includes all three provenance fields populated and traceable back to the exact source document.

**Acceptance Scenarios**:

1. **Given** two corporate manuals ingested by two isolated subagents, **When** the aggregator requests claim extraction, **Then** the output is a JSON array of claims where each entry contains non-empty `claim`, `source_url`, `source_name`, and `publication_date` fields.
2. **Given** a single factual claim appears in a source manual, **When** the pipeline emits it, **Then** the emitted record links back to the exact source document and is not merged into a prose summary.
3. **Given** an aggregation of N manuals, **When** the output is inspected, **Then** zero claims appear without provenance metadata (no amalgamated paragraphs, no orphan sentences).

---

### User Story 2 - Conflict Surfacing Without Silent Resolution (Priority: P2)

A practitioner deliberately seeds two manuals with contradictory numbers for the same quantity. The aggregated output flags the disagreement with an explicit `conflict_detected=true` marker, preserves both claims under their original provenance JSON blocks, and routes the resolution to a human coordinator instead of silently picking a winner.

**Why this priority**: This directly defends the primary anti-pattern of Kata 20 — the model "arbitrarily picking" a truth when sources disagree. Surfacing conflicts keeps the human in the loop (Constitution VII) and prevents fabricated consensus.

**Independent Test**: Can be fully tested by planting two contradictory facts across two manuals, running the aggregation, and asserting both original claims (with provenance) are present in the output under a `conflict_detected` block with a human-review hand-off, and that neither claim has been dropped or merged.

**Acceptance Scenarios**:

1. **Given** two manuals with conflicting numeric claims for the same fact, **When** aggregation completes, **Then** the output contains a `conflict_detected=true` marker with both claims as full provenance records.
2. **Given** a detected conflict, **When** the pipeline reports it, **Then** a human-review task is created and the pipeline does NOT emit a single "winning" value.
3. **Given** two sources agree, **When** aggregated, **Then** no `conflict_detected` marker is emitted (no false positives).

---

### User Story 3 - Fail-Closed on Missing Provenance Schema (Priority: P3)

A practitioner removes one or more provenance fields (`source_url`, `source_name`, or `publication_date`) from the extraction schema request. The pipeline refuses to proceed rather than emit orphan claims, returning a schema-validation failure that names the missing fields.

**Why this priority**: This defends the schema-enforced-boundary principle (Constitution II) and prevents a regression where a practitioner accidentally loosens the contract and silently loses metadata. The pipeline must fail closed.

**Independent Test**: Can be fully tested by submitting a schema missing a required provenance field and verifying the pipeline raises a structured validation error (not a warning, not partial output) that lists the omitted field(s).

**Acceptance Scenarios**:

1. **Given** a schema that omits `source_url`, **When** the pipeline is invoked, **Then** execution halts with a validation error naming the missing field, and no claims are emitted.
2. **Given** a schema missing `publication_date`, **When** the pipeline runs, **Then** a fail-closed error is returned and zero partial results leak downstream.
3. **Given** a fully-specified schema, **When** the pipeline runs, **Then** it proceeds normally with provenance-complete output.

---

### Edge Cases

- What happens when a source document lacks a `publication_date` field (e.g., undated internal memo)? The claim MUST be retained with an explicit sentinel (`publication_date: "unknown"` or equivalent) rather than silently dropped or fabricated.
- How does the system handle a `source_url` that is a local file path rather than an HTTP(S) URL? The value MUST be preserved verbatim and flagged as a non-web source; the pipeline MUST NOT invent a URL.
- What happens when two different sources produce identical claim text? Both provenance records MUST be preserved as separate entries; deduplication MUST NOT strip source metadata.
- How does the system handle an internal-only source with no URL at all? The claim MUST be emitted with `source_url: null` and `source_name` populated, and the pipeline MUST NOT discard the claim nor fabricate a URL.
- What happens when a subagent returns a prose summary instead of structured claims? The aggregator MUST reject the subagent's output as a schema violation and MUST NOT attempt to "parse" prose back into claims.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST emit every factual claim as a structured record containing `claim`, `source_url`, `source_name`, and `publication_date` fields, all populated from the originating source.
- **FR-002**: System MUST reject any claim that lacks one or more required provenance fields and MUST NOT emit orphan claims downstream.
- **FR-003**: System MUST detect conflicts — defined as numeric-token divergence within a `canonical_key` group (two or more claims asserting contradictory numeric values for the same underlying fact) — and mark them with an explicit `conflict_detected=true` flag in the output. Categorical-contradiction detection is out of scope for this kata (see Clarifications).
- **FR-004**: System MUST NOT auto-resolve detected conflicts by picking a source heuristically, by recency, by majority vote, or by any model-internal preference.
- **FR-005**: System MUST route every detected conflict to a human coordinator as an explicit review task, preserving both (or all) original provenance JSON blocks in the hand-off payload.
- **FR-006**: System MUST log every aggregation pass with the set of source documents consulted, the number of claims emitted, and the number of conflicts surfaced, for self-audit and provenance replay.
- **FR-007**: System MUST forbid subagents from producing amalgamated prose summaries as their output contract; subagent outputs MUST be schema-validated JSON claim lists.
- **FR-008**: System MUST preserve duplicate claims from different sources as separate provenance records rather than deduplicating them into a single metadata-less entry.

### Key Entities *(include if feature involves data)*

- **Source Document**: A single corporate manual or reference artifact ingested by exactly one subagent. Attributes: document identifier, canonical name, URL or path, publication date (may be "unknown").
- **Claim**: A single factual assertion extracted from a Source Document. Attributes: claim text, link to exactly one Provenance Record. A Claim with no Provenance Record is invalid and MUST be rejected.
- **Provenance Record**: The metadata bundle binding a Claim to its Source Document. Attributes: `source_url`, `source_name`, `publication_date`. All three fields are required by contract.
- **Conflict Set**: A grouping of two or more Claims that make contradictory assertions about the same underlying fact. Attributes: `conflict_detected=true` marker, the full list of participating Claims with their Provenance Records, and a reference to the associated Review Task.
- **Review Task**: A human-coordinator hand-off generated for each Conflict Set. Attributes: conflict identifier, participating provenance blocks, timestamp, status (open/resolved), and the resolving human's decision once closed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of emitted claims have populated `source_url`, `source_name`, and `publication_date` fields across the full labeled corpus.
- **SC-002**: 0 auto-resolved conflicts across the labeled corpus — every seeded contradiction surfaces as an explicit `conflict_detected` record routed to human review.
- **SC-003**: Conflict detection recall is `100%` on the seeded conflict set — every planted contradiction surfaces as a `conflict_detected=true` record and zero seeded contradictions are missed (see Clarifications).
- **SC-004**: Orphan-claim rejection rate equals 100% on the negative test set — every schema request missing a required provenance field fails closed with a structured validation error.
