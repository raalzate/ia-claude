# Feature Specification: Defensive Structured Extraction with JSON Schemas

**Feature Branch**: `005-defensive-extraction`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 5 — Force the model to extract unstructured information into a predictable, schema-governed format WITHOUT fabricating data. Use schema-enforced tool calls, a forced tool choice, mark only guaranteed fields as required, allow nullable unions for optional fields, and provide escape enumerations (e.g., `other`, `unclear`) paired with a details field for ambiguous input."

## User Stories *(mandatory)*

<!--
  Prioritized user journeys. Each story is independently testable and demonstrable.
  The MVP is P1: a single extraction round-trip that returns a schema-valid object.
  P2 and P3 harden the feature against the two most common failure modes:
  fabrication for missing optionals, and misclassification of ambiguous values.
-->

### User Story 1 - Well-Formed Source Produces Schema-Valid Record (Priority: P1)

A practitioner supplies an unstructured source document that contains every guaranteed field described by the extraction schema. The system invokes the model with a schema-bound extraction tool and a forced tool choice, and returns a typed object that conforms exactly to the declared schema.

**Why this priority**: Without a working happy path that produces a schema-valid object, no downstream consumer can rely on the extractor at all. This is the minimum viable slice of the kata and proves that Constitutional Principle II (Schema-Enforced Boundaries) is satisfied for the baseline case.

**Independent Test**: Feed the extractor a corpus item whose text contains every required field. Verify the returned record validates against the declared extraction schema, that no field outside the schema is present, and that the tool-call envelope was actually used (not free-form text).

**Acceptance Scenarios**:

1. **Given** a source document that contains every guaranteed field, **When** the practitioner runs extraction with the schema-bound tool and forced tool choice, **Then** the returned record validates against the extraction schema with zero validation errors.
2. **Given** a source document with all required fields present, **When** the model is invoked, **Then** the model's response is delivered as a tool call (not a free-text message) and contains only keys declared by the schema.
3. **Given** a valid extraction result, **When** it is passed to schema validation, **Then** every required field has a non-null value of the declared type.

---

### User Story 2 - Missing Optional Fields Return Null, Not Fabrications (Priority: P2)

A practitioner supplies a source document that omits one or more optional fields. The extractor returns those fields as `null` via nullable union types rather than inventing plausible-sounding values. This is the primary defense against the kata's first anti-pattern (marking every field as required).

**Why this priority**: Fabrication is the highest-severity defect this feature exists to prevent. A feature that hallucinates optional fields is strictly worse than no feature at all, because downstream consumers trust the schema. This story operationalizes Constitutional Principle VII (Provenance & Self-Audit): absence must be representable.

**Independent Test**: Curate a subset of the test corpus where selected optional fields are known to be absent from the source text. Run extraction and verify that every absent optional field arrives as `null`, and that no plausible-looking fabricated value is substituted.

**Acceptance Scenarios**:

1. **Given** a source document that omits an optional field, **When** extraction runs, **Then** that field is returned as `null` in the extracted record.
2. **Given** a schema declaring an optional field as a nullable union, **When** the source lacks that information, **Then** the model returns `null` rather than a free-form guess or the string "unknown".
3. **Given** an extraction result over a corpus of sources with known-absent optionals, **When** the batch completes, **Then** the null rate on those fields meets the success criterion and no fabricated values are observed.

---

### User Story 3 - Ambiguous Values Route to Escape Enum (Priority: P3)

A practitioner supplies a source document whose value for an enumerated field does not clearly match any enumerated option, or is contradicted elsewhere in the text. The extractor returns the escape option (`"unclear"` or `"other"`) for that field and populates the paired details field with the ambiguous raw value for downstream human review.

**Why this priority**: Without an escape hatch, the model is forced to pick the nearest enum value, silently corrupting the data. This story closes the ambiguity gap that would otherwise masquerade as clean data, and makes the extraction output auditable per Constitutional Principle VII.

**Independent Test**: Feed the extractor ambiguity fixtures (value outside the enumerated set, contradictory statements, mixed-language phrasing). Verify the enumerated field contains the declared escape option and the paired details field contains a non-empty string capturing what was actually seen.

**Acceptance Scenarios**:

1. **Given** a source whose enumerated value does not appear in the declared enum, **When** extraction runs, **Then** the field is set to `"other"` (or `"unclear"`) and the paired details field is populated.
2. **Given** a source with contradictory statements about an enumerated field, **When** extraction runs, **Then** the escape option is selected and the details field captures the contradiction verbatim or summarized.
3. **Given** an ambiguous corpus, **When** the batch completes, **Then** 100% of ambiguous cases are routed through the escape enum rather than being forced into a concrete category.

---

### Edge Cases

- **Missing required field**: The source omits a field declared as `required`. The extractor MUST fail schema validation and surface the failure to the caller; it MUST NOT silently coerce the field to `null` or to a default, because required means guaranteed-present per this feature's contract.
- **Value outside enumerated set**: The source contains an enumerated-field value that is not in the declared enum (and no escape option applies). The extractor MUST route to the escape option and populate the details field; it MUST NOT emit an out-of-enum string, which would violate the schema.
- **Mixed-language source**: The source mixes languages (e.g., Spanish and English). The extractor MUST either extract faithfully in the source language or route to the escape enum with a details field explaining the language mix; it MUST NOT translate values silently.
- **Contradictory statements**: The source asserts two different values for the same field. The extractor MUST route to the escape enum with both contradictory values preserved in the details field.
- **Empty source**: The source document is empty or contains no extractable content. The extractor MUST fail schema validation on any required field and MUST NOT emit a record of fabricated defaults.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST declare a formal extraction schema for every extraction task, enumerating every permitted field, its type, and whether it is required or optional.
- **FR-002**: The system MUST invoke the model with a schema-bound extraction tool and a forced tool choice that guarantees the model returns a tool call conforming to the schema (no free-text fallback).
- **FR-003**: The system MUST mark a field as `required` only when that field is guaranteed present in every source document of the target domain.
- **FR-004**: The system MUST declare optional fields using a nullable union type so the model can explicitly return absence, and MUST NOT declare optional fields as plain string types.
- **FR-005**: The system MUST provide an escape enumeration option (e.g., `"other"`, `"unclear"`) on every **enumerated field in the declared schema**, and MUST pair it with a details field capable of capturing the ambiguous raw value.
- **FR-006**: The system MUST validate every model output against the declared extraction schema and MUST reject outputs that fail validation rather than silently coercing them.
- **FR-007**: The system MUST NOT accept free-text "best guess" content for missing optional fields; any optional field without explicit evidence in the source MUST be `null`.
- **FR-008**: The system MUST surface schema validation failures to the caller with sufficient context to audit which field failed and why (Principle VII, Provenance & Self-Audit).
- **FR-009**: The system MUST document, for each extraction schema, which fields are guaranteed vs. optional and what the escape option means (Principle VIII, Docs), so reviewers can verify the required/optional split is defensible.
- **FR-010**: The system MUST refuse to emit fields outside the declared schema, even if the model attempts to return additional keys.

### Key Entities

- **Source Document**: The unstructured input supplied to the extractor. Carries free-form content in one or more languages and may contain missing, ambiguous, or contradictory information. Opaque to the schema.
- **Extraction Schema**: The declared contract that governs a single extraction task. Enumerates fields, types, required vs. optional status, nullable unions, enumerated options, and escape options. Functions as the single source of truth for "what counts as a valid record".
- **Extracted Record**: A typed object produced by a successful extraction. Conforms exactly to its Extraction Schema. Required fields are present and non-null; optional fields are either present-and-typed or `null`; enumerated fields contain either a declared option or the escape option.
- **Ambiguity Marker**: The combination of an enumerated field set to its escape option (`"other"` / `"unclear"`) and its paired details field populated with the observed raw value. Makes ambiguity a first-class, auditable signal rather than a hidden coercion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Zero fabricated values are observed across the full test corpus (no value in an extracted record lacks textual support in its source document). (Asserted on the labeled fixture corpus; the `LIVE_API=1` path is advisory.)
- **SC-002**: 100% of extraction outputs that reach the caller are schema-valid against their declared Extraction Schema.
- **SC-003**: 100% of ambiguous cases in the ambiguity fixture set are routed to the escape enum (with the paired details field populated) rather than forced into a concrete enumerated option.
- **SC-004**: The null rate on absent optional fields is at least 99% across the test corpus (absent optionals are faithfully reported as `null` rather than fabricated).
