# Feature Specification: Critical Evaluation & Self-Correction

**Feature Branch**: `015-self-correction`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 15 — Prevent mathematical hallucinations by forcing the model to cross-audit its own internal computations against stated values in the source. Applied to an invoice-extraction scenario where the stated total must be reconciled against the sum of line items, with a conflict flag routing mismatches to human review."

## User Stories *(mandatory)*

<!--
  User stories are prioritized user journeys. Each story is independently testable —
  implementing any single story should still yield a viable slice of value.
-->

### User Story 1 - Consistent Invoice Passes Cross-Audit (Priority: P1)

A practitioner submits an invoice whose stated total matches the arithmetic sum of its line items. The extraction produces both the literal `stated_total` read from the document and the independently `calculated_total` derived by summing line items, and reports that no conflict was detected. The practitioner gains confidence that the pipeline is actually performing the recomputation (not just echoing the stated figure back) because both values are surfaced separately and agree.

**Why this priority**: This is the happy-path backbone of the self-correction mechanism. Without it, neither the conflict-detection nor the human-review paths can be trusted. It also establishes the schema shape that Stories 2 and 3 depend on.

**Independent Test**: Can be fully tested by feeding a known-consistent invoice into the extractor and asserting that `stated_total`, `calculated_total`, and `conflict_detected=false` are all emitted, with both totals numerically equal within the declared tolerance.

**Acceptance Scenarios**:

1. **Given** an invoice whose line items sum exactly to the stated total, **When** the extractor runs, **Then** it emits `stated_total` matching the document's literal value, `calculated_total` equal to the sum of line items, and `conflict_detected=false`.
2. **Given** an invoice with rounding differences within the declared tolerance, **When** the extractor runs, **Then** both totals are emitted verbatim (neither overwritten) and `conflict_detected=false`.
3. **Given** the extraction succeeds, **When** the output is inspected, **Then** a per-line-item calculation trace is attached for audit.

---

### User Story 2 - Conflicting Invoice Routes to Human Review (Priority: P2)

A practitioner submits an invoice whose line items sum to a value different from the stated total (for example, a missing line, a transcription error, or a fraudulent alteration). The extractor detects the mismatch, sets `conflict_detected=true`, preserves BOTH totals exactly as produced, and routes the record to a human-review queue instead of returning a "clean" extraction. This is the primary anti-pattern defense: the system refuses to silently trust either number.

**Why this priority**: This is the core value proposition of the kata. It converts a silent hallucination-prone pipeline into one that fails loudly and safely.

**Independent Test**: Can be fully tested by feeding a curated invoice where the stated total disagrees with the line-item sum beyond tolerance, and asserting that `conflict_detected=true`, both totals remain unchanged, and the record appears in the human-review queue.

**Acceptance Scenarios**:

1. **Given** an invoice whose stated total disagrees with the line-item sum beyond the declared tolerance, **When** the extractor runs, **Then** `conflict_detected=true` is emitted and the record is routed to the human-review queue.
2. **Given** a conflict is detected, **When** the output is inspected, **Then** `stated_total` and `calculated_total` are both present and neither has been replaced by the other.
3. **Given** a conflict is detected, **When** downstream consumers read the record, **Then** they receive the full line-item calculation trace so a reviewer can pinpoint the discrepancy.

---

### User Story 3 - Neither Total Is Ever Silently Overwritten (Priority: P3)

A practitioner auditing the pipeline needs to guarantee that the extractor never "helpfully" replaces the stated total with the calculated one (or vice versa) under any input condition — consistent, conflicting, rounding-only, or degenerate. Both values must travel through the system as independent fields so that a reviewer can always reconstruct what the document said and what the model computed.

**Why this priority**: This closes the second half of the anti-pattern — silently overwriting one total with the other would defeat the audit trail even when `conflict_detected` is correctly set. It is P3 because it is enforced primarily through schema and invariant checks rather than new user-facing behavior.

**Independent Test**: Can be fully tested by replaying a corpus of invoices (consistent, conflicting, rounding-only, degenerate) and asserting for every record that `stated_total` equals the literal document value and `calculated_total` equals the recomputed sum, with zero cases of one field being substituted by the other.

**Acceptance Scenarios**:

1. **Given** any invoice in the test corpus, **When** the extractor runs, **Then** `stated_total` always reflects the literal document value and `calculated_total` always reflects the independent recomputation.
2. **Given** a conflict is detected, **When** the record is persisted, **Then** no post-processing step collapses the two fields into one.
3. **Given** a consistent invoice, **When** the record is persisted, **Then** the two fields are still emitted as distinct values even though they agree.

---

### Edge Cases

- **Missing line items**: What happens when the document has a stated total but no extractable line items? The extractor MUST NOT fabricate a `calculated_total` of zero that silently matches; it should flag the record for review.
- **Non-numeric amounts**: How does the system handle line items whose amounts are unparseable (e.g., "TBD", "see attached")? Such lines must not be silently treated as zero.
- **Currency mismatches**: What happens when line items are expressed in a different currency than the stated total, or currencies are mixed within line items? A conflict must be detected rather than coerced.
- **Rounding-only discrepancies**: How does the system distinguish a legitimate rounding gap from a real error? A declared tolerance governs this, and the tolerance itself is logged alongside the totals.
- **Very long invoices**: What happens when an invoice has hundreds of line items and the model is tempted to shortcut the sum? The line-item calculation trace must cover every line, not a summarized subset.
- **Negative or credit line items**: How are credits, refunds, and discounts handled? They must be included in `calculated_total` with their sign preserved.
- **Duplicate line items**: What happens when the same line appears twice? Both occurrences contribute to the sum; the trace must show both.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST emit both `stated_total` (the literal total as written in the source document) and `calculated_total` (the independently recomputed sum of line items) as distinct fields on every extraction output.
- **FR-002**: System MUST iteratively extract each line item and sum the line-item amounts to produce `calculated_total`, independent of `stated_total`.
- **FR-003**: System MUST include a boolean `conflict_detected` field in the extraction schema on every output.
- **FR-004**: System MUST set `conflict_detected=true` whenever `stated_total` and `calculated_total` disagree beyond a declared, documented tolerance, and `conflict_detected=false` otherwise.
- **FR-005**: System MUST route every record with `conflict_detected=true` to a human-review queue and MUST NOT return it as a clean extraction to downstream consumers.
- **FR-006**: System MUST NEVER silently replace `stated_total` with `calculated_total`, nor `calculated_total` with `stated_total`, under any condition (anti-pattern defense).
- **FR-007**: System MUST log a per-line-item calculation trace (each line's extracted amount and its contribution to the running sum) on every extraction, to satisfy Provenance & Self-Audit.
- **FR-008**: System MUST declare and persist the tolerance value used for the conflict comparison alongside the extraction output.
- **FR-009**: System MUST emit a machine-readable schema-conformant record; any extraction that cannot populate both totals MUST be flagged as a conflict rather than returned with null coerced to zero.
- **FR-010**: System MUST preserve the sign of credit / refund / discount line items when computing `calculated_total`.

### Key Entities *(include if feature involves data)*

- **Invoice**: A source document being extracted; carries a literal stated total, zero or more line items, and metadata (currency, date, issuer).
- **Line Item**: A single row of the invoice with an extractable amount; contributes to `calculated_total` with its sign preserved.
- **Totals Pair**: The paired `stated_total` and `calculated_total` fields; always emitted together, never collapsed into a single field.
- **Conflict Flag**: The boolean `conflict_detected`; set by comparing the Totals Pair against the declared tolerance.
- **Review Task**: A record placed on the human-review queue when `conflict_detected=true`; carries the Invoice, the Totals Pair, the line-item calculation trace, and the tolerance used.
- **Calculation Trace**: An ordered, per-line-item log of extracted amounts and the running sum, attached to every extraction for audit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `conflict_detected` accuracy is greater than or equal to the target threshold on the labeled test set (both true-positive and true-negative rates measured independently against curated consistent and conflicting invoices).
- **SC-002**: Zero silent overwrites across the test corpus — for every record, `stated_total` equals the literal document value and `calculated_total` equals the independent recomputation, with no case of one field being substituted by the other.
- **SC-003**: 100% of conflicts produce a traceable line-item calculation log sufficient for a human reviewer to locate the discrepancy without re-running the extraction.
- **SC-004**: The human-review queue receives every record flagged with `conflict_detected=true`, with zero flagged records leaking to downstream "clean" consumers.
