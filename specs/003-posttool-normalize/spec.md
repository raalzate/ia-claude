# Feature Specification: Cognitive Load Normalization via PostToolUse Hooks

**Feature Branch**: `003-posttool-normalize`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 3 — Reduce token saturation and prevent hallucinations when external tools return noisy or legacy-format data by intercepting tool responses with a PostToolUse hook, stripping legacy markup, mapping arcane status codes to human-readable strings, and attaching a minimal, clean JSON object to the model's conversation history."

## User Stories *(mandatory)*

### User Story 1 - Practitioner sees a clean, minimal JSON instead of raw legacy output (Priority: P1)

A practitioner invokes the legacy data tool from within an agent session. Before the tool's response reaches the model's context, a PostToolUse hook intercepts it, strips all legacy markup, resolves every arcane status code into a human-readable string, and attaches a compact JSON object to the conversation history. The model never observes the raw heterogeneous legacy payload.

**Why this priority**: This is the core value of the kata and the primary defense against Principle II (Schema-Enforced Boundaries) and Principle III (Context Economy) violations. Without P1 the feature does not exist, and the model is left to parse noisy legacy data on every turn — the exact anti-pattern the kata targets.

**Independent Test**: Can be fully tested by calling the legacy data tool with a representative legacy payload, capturing the message that lands in the model's conversation history, and verifying it is a schema-conformant JSON object with no legacy markup and fully resolved status text. Delivers immediate value even without the other stories.

**Acceptance Scenarios**:

1. **Given** the agent is wired to a legacy data source that returns heterogeneous markup blocks and arcane status codes, **When** the practitioner triggers a tool call and the PostToolUse hook runs, **Then** the message appended to the model's conversation history is a minimal JSON object with no legacy markup characters and every status code replaced by a human-readable string.
2. **Given** the hook is active, **When** a tool response contains a recognized status code, **Then** the normalized JSON contains the mapped human-readable label rather than the raw code.
3. **Given** the hook is active, **When** the practitioner inspects the conversation history after a tool call, **Then** no raw legacy block from the source is present in model context.

---

### User Story 2 - Practitioner compares baseline vs. normalized runs and observes the anti-pattern defense (Priority: P2)

A practitioner runs the same task twice — once with the PostToolUse hook disabled (baseline, raw legacy payload injected directly into history — the anti-pattern) and once with the hook enabled (normalized). They compare token usage of the tool-response messages and the rate of downstream misinterpretations by the model.

**Why this priority**: Makes the anti-pattern (raw, noisy, legacy-formatted responses pushed into context so the model "figures it out" every turn) concrete and measurable. Directly enforces Principle III (Context Economy) and Principle VIII (Docs) by producing a comparison artifact, but the feature is usable for P1 alone.

**Independent Test**: Can be fully tested by toggling the hook on/off across two otherwise-identical runs, recording the token count of the tool-response message and the count of downstream misinterpretation events, and verifying the normalized run is strictly smaller on both axes.

**Acceptance Scenarios**:

1. **Given** two identical agent runs over the same legacy payload, **When** the hook is disabled in the first and enabled in the second, **Then** the tool-response token count is substantially lower in the normalized run.
2. **Given** the comparison output, **When** downstream model misinterpretations are counted (decisions based on misread legacy markup or unresolved codes), **Then** the normalized run records fewer such misinterpretations than the baseline.
3. **Given** the practitioner reviews both runs, **When** they examine the baseline conversation history, **Then** the raw legacy block is visibly present — documenting the anti-pattern — and the normalized run contains only the clean JSON.

---

### User Story 3 - Practitioner adds a new status code mapping without touching the model (Priority: P3)

A practitioner discovers a new arcane status code emitted by the legacy source. They add a single entry to the normalization map and re-run the tool. The new code flows through the hook, is resolved to its human-readable string, and appears correctly in the minimal JSON — with no change to prompts, model configuration, or agent wiring.

**Why this priority**: Validates that the normalization map is a genuine schema boundary (Principle II) and that extending coverage is a configuration change, not a model change. Nice-to-have for the kata but proves the design scales; the feature still delivers without it.

**Independent Test**: Can be fully tested by adding one entry to the normalization map, triggering a tool response that emits the new code, and verifying the resolved string appears in the normalized JSON — with no edits to any prompt or model-facing artifact.

**Acceptance Scenarios**:

1. **Given** the normalization map is extended with a new status code → human-readable string pair, **When** the tool returns a payload containing that code, **Then** the normalized JSON contains the mapped string.
2. **Given** the new mapping was added, **When** the practitioner diffs the change, **Then** only the normalization map is modified — no prompts, no model settings, no agent wiring.

---

### Edge Cases

- What happens when the legacy source returns **malformed markup** (unclosed tags, mismatched delimiters, or truncated blocks)? The hook must not crash; it must emit a normalized JSON flagged as parse-degraded and still preserve the original in the audit trail.
- What happens when the response contains an **unknown status code** not present in the normalization map? The hook must surface it as an explicit "unknown" marker (never a guessed label) and keep the raw code in the audit record.
- What happens when the tool returns an **empty response** (no body, no codes, no markup)? The hook must produce a well-formed, schema-conformant JSON representing the empty state rather than skipping the append.
- What happens when the payload is **very large** (well beyond typical)? The hook must normalize within bounded memory, the normalized JSON must remain minimal, and the audit trail must still retain the full original.
- What happens with **nested structures** (legacy blocks embedded inside other legacy blocks, or multiple status codes per response)? The hook must traverse the nesting, resolve every code it encounters, and produce a flat or shallow minimal JSON — never re-emit nested legacy markup.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST intercept every tool response from the legacy data source via a PostToolUse hook before that response reaches the model's context.
- **FR-002**: The system MUST produce a schema-conformant minimal JSON object for every intercepted response, where "schema-conformant" means it adheres to a single documented shape with a bounded field set.
- **FR-003**: The system MUST map all known arcane status codes to human-readable strings using an explicit normalization map, and MUST surface unknown codes as an explicit "unknown" marker with the raw code retained — never a guessed or fabricated label.
- **FR-004**: The system MUST NOT pass raw legacy formats (markup blocks, arcane codes, heterogeneous payloads) downstream into the model's conversation history under any circumstance, including parse failures and empty responses.
- **FR-005**: The system MUST log the original, unmodified tool payload to an audit record for every intercepted response, even when the normalized form is what is delivered to the model, so that 100% of originals remain retrievable for review.
- **FR-006**: The system MUST attach the normalized JSON to the model's conversation history in place of the original tool response, preserving working memory by keeping the injected message minimal.
- **FR-007**: The system MUST handle malformed, empty, unknown-code, nested, and oversized payloads without crashing and without leaking raw legacy content into model context.

### Key Entities

- **Tool Response**: The raw payload returned by the legacy data source. May contain heterogeneous legacy markup blocks, arcane status codes, nested structures, or be empty/malformed. Entirely opaque to the model — never reaches it directly.
- **Normalization Map**: The configuration artifact that pairs each known arcane status code with its human-readable string. Extending coverage is a data change, not a code or model change.
- **Normalized Payload**: The minimal, schema-conformant JSON object produced by the hook. Contains resolved status labels, cleaned content, and explicit markers for unknown codes or degraded parses. This is the only form the model observes.
- **Audit Record**: The retained copy of the original Tool Response plus metadata (timestamp, tool invocation reference, parse status). Enables after-the-fact review, debugging, and anti-pattern demonstrations without polluting the model's context.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The token count of the normalized payload is no more than 30% of the token count of the corresponding raw tool response, measured across a representative sample of legacy payloads.
- **SC-002**: Zero raw legacy markup blocks reach model context across all runs with the hook enabled — verified by scanning every message appended to the conversation history.
- **SC-003**: Unknown status codes surface in the normalized payload as an explicit "unknown" marker in 100% of cases, with no guessed or fabricated human-readable labels.
- **SC-004**: The audit trail retains 100% of original tool responses, byte-for-byte recoverable, even when the normalized form delivered to the model is degraded, empty, or trimmed.

## Clarifications

- **SC-001 measurement shape**: The ≤30% ceiling (equivalently, ≥70% reduction) is a **corpus average**, not a per-fixture bound. Tiny or empty payloads may individually over- or undershoot the threshold; what is asserted is the mean normalized/raw token ratio across the representative fixture corpus.
