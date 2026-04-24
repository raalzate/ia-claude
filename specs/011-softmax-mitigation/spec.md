# Feature Specification: Softmax Dilution Mitigation

**Feature Branch**: `011-softmax-mitigation`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 11 — Softmax Dilution Mitigation (Edge Placement + Proactive Compaction). Protect critical business rules from the 'lost in the middle' blind spot caused by the U-shaped attention curve in transformers by relocating hard constraints to the prompt edges and proactively compacting long sessions at 50–60% capacity."

## Clarifications

### 2026-04-24 (phase-06 analyze)

- **FR-002 / SC-003 trigger band**: the proactive-compaction band is the half-open interval `[0.55, 0.60)`. The trigger fires at `usage_fraction >= 0.55`; `CompactionEvent.fired_at_usage_fraction` MUST lie in `[0.55, 0.60)`; reaching `usage_fraction > 0.60` without a prior `CompactionEvent` is a fail-closed condition.
- **SC-001 adversarial batch size**: the adversarial batch size is pinned at `N=30` trials per layout (matching `plan.md` Performance Goals and `tasks.md` T049/T052), so the ≥95% rate is reproducible.
- **F-003 edit-time regression scenario (anti-pattern slips back in)**: RESOLVED (2026-04-24) — `/iikit-04-testify` re-run added TS-015 and TS-016 to `tests/features/antipattern_mid_buried_rule.feature`: render-time detection raises `EdgePlacementViolation` with `regression_kind="mid_burying"` and logs a `RegressionFinding` carrying `rule_id`, `previous_position`, `candidate_position`, `detected_at`. Assertion-integrity hash refreshed.

## User Stories *(mandatory)*

### User Story 1 - Edge Placement of Critical Rule (Priority: P1)

A practitioner authors a long prompt that contains a single hard, non-negotiable business rule (an absolute guardrail). Following the edge-placement pattern, the practitioner deliberately anchors that rule at both the primacy edge (very top of the prompt) and the latency edge (very bottom, just before the user turn). The practitioner then runs a representative set of requests that try, both directly and indirectly, to elicit a response that would violate the rule, and verifies the model obeys the rule consistently across the run.

**Why this priority**: This is the baseline defense against the softmax-dilution failure mode. If critical rules are not anchored at the edges, every downstream mitigation (compaction, re-anchoring, logging) is operating on an already-compromised prompt. P1 delivers the minimum viable protection on its own.

**Independent Test**: Can be fully tested by (a) declaring one critical rule, (b) rendering a long prompt with the rule placed only at the extremes, (c) issuing a batch of adversarial/ambiguous requests, and (d) measuring the rule-compliance rate against the 95% target. No compaction logic is required for this story to deliver value.

**Acceptance Scenarios**:

1. **Given** a declared critical rule and a long prompt rendered with edge placement enabled, **When** the practitioner submits the adversarial request batch, **Then** the observed rule-compliance rate is ≥ 95%.
2. **Given** a long prompt whose body contains content that implicitly contradicts the critical rule, **When** the rule is anchored at both edges, **Then** the model defers to the edge-anchored rule rather than the contradictory mid-prompt content.

---

### User Story 2 - Anti-Pattern Demonstration: Rule Buried in the Middle (Priority: P2)

The practitioner runs a controlled variant of the P1 scenario in which the same critical rule is deliberately placed in the middle of the prompt, with no edge anchoring. The practitioner executes the same adversarial batch and records the violation rate. The system surfaces the delta between mid-placement and edge-placement so the softmax-dilution effect is visible and the defense (edge placement) is justified empirically.

**Why this priority**: The defense only becomes convincing when the attack is demonstrated. P2 proves the "lost in the middle" phenomenon on the practitioner's own workload and produces the empirical gap that motivates P1. It is secondary because P1 alone already delivers protection; P2 delivers the explanation and the regression signal.

**Independent Test**: Can be fully tested by rendering the prompt with the rule in the middle, running the same adversarial batch used in P1, and computing the compliance delta against the P1 run. Passes when the drop is ≥ 20 percentage points.

**Acceptance Scenarios**:

1. **Given** the same critical rule, adversarial batch, and base prompt from P1, **When** the rule is placed in the middle third of the prompt instead of the edges, **Then** the observed compliance rate drops by ≥ 20 percentage points (Δ ≥ 0.20).
2. **Given** the mid-placement run completes, **When** the practitioner reviews the output, **Then** a clearly labelled anti-pattern report is produced that names the violations and attributes them to mid-context burying.

---

### User Story 3 - Proactive Compaction and Re-Anchoring (Priority: P3)

During a long multi-turn session, context usage grows past roughly 55% of the model's working window. Before attention rot sets in, the system proactively compacts older turns into a summary while preserving the critical rules verbatim, and re-renders the compacted prompt with those rules re-anchored at both edges. The practitioner verifies that, after compaction, the rules are still obeyed with the same compliance level observed in P1.

**Why this priority**: Compaction is only meaningful after the edge-placement and anti-pattern-detection foundations are in place. P3 extends protection from single-shot prompts to long-running sessions. It is last because it presupposes the rules, thresholds, and measurement harness produced by P1 and P2.

**Independent Test**: Can be fully tested by scripting a session that drives usage past the declared compaction threshold, asserting that a compaction event fires before 60%, inspecting the post-compaction prompt for the verbatim critical rules at both edges, and re-running a sample of the P1 adversarial batch against the compacted session.

**Acceptance Scenarios**:

1. **Given** an active session whose token usage crosses the 50–60% compaction band, **When** the next turn is prepared, **Then** a compaction event fires before usage exceeds 60%.
2. **Given** a compaction event has just completed, **When** the post-compaction prompt is rendered, **Then** every declared critical rule is present verbatim at both the primacy and latency edges.
3. **Given** a re-anchored post-compaction prompt, **When** the P1 adversarial batch is replayed, **Then** the compliance rate is not materially lower than the pre-compaction P1 rate.

---

### Edge Cases

- **Critical rule longer than edge budget**: A declared critical rule exceeds the token budget reserved for an edge region. The system must not silently truncate the rule; it must either reject the configuration or degrade in a declared, auditable way.
- **Compaction collapses critical rule**: The summarizer rewrites or paraphrases the critical rule during compaction, weakening its guardrail semantics. The system must preserve critical rules verbatim and detect any drift.
- **Multi-rule competition for edge real estate**: Multiple critical rules are declared and their combined size exceeds the available edge budget. The system must apply a declared priority ordering and surface which rules were placed versus deferred.
- **Session reaches 100% before compaction fires**: The compaction trigger fails or is starved, and the session reaches the hard context limit with critical rules still buried in the middle. The system must fail closed by refusing the turn via `CompactionOverdue` rather than silently dropping edge anchoring.
- **Anti-pattern slips back in**: A later edit reintroduces mid-context burying of a critical rule. The system must detect this regression at render time and block or warn before the prompt is dispatched.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST place every declared critical rule at both the primacy edge (top) and the latency edge (bottom) of every rendered prompt.
- **FR-002**: System MUST run automatic compaction when session context usage crosses a declared capacity threshold within the half-open interval `[0.55, 0.60)` (fires at `usage_fraction >= 0.55`), and MUST complete compaction before usage exceeds 60%.
- **FR-003**: System MUST re-anchor every declared critical rule verbatim at both edges of the post-compaction prompt.
- **FR-004**: System MUST log every edge-placement decision and every compaction event with enough detail (rule identity, placement position, capacity at trigger, rules preserved) to audit compliance after the fact.
- **FR-005**: System MUST reject, or fail closed on, any content or configuration that would push a declared critical rule out of an edge region or cause it to be buried in the middle of the prompt.
- **FR-006**: System MUST expose a mid-placement anti-pattern mode for demonstration purposes that is clearly labelled as such and cannot be enabled in production runs without an explicit opt-in flag.
- **FR-007**: System MUST record, per run, the rule-compliance rate and the delta between edge-placement and mid-placement runs so the softmax-dilution effect is measurable.

### Key Entities *(include if feature involves data)*

- **Critical Rule**: A hard, non-negotiable constraint the model must obey. Attributes include an identifier, the verbatim rule text, a priority for edge-budget competition, and a compliance target.
- **Edge Region**: A bounded portion of the prompt at either the primacy (top) or latency (bottom) end, with a declared token budget and an ordered list of rules currently placed inside it.
- **Compaction Event**: A record of a proactive compaction, including the capacity percentage at which it fired, the turns collapsed, the summary produced, and the rules re-anchored afterwards.
- **Attention Profile**: A descriptor of the assumed U-shaped attention curve for the target model, used to justify the edge-region budgets and the compaction threshold band.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Rule compliance under edge placement is ≥ 95% across the adversarial batch.
- **SC-002**: Compliance drop between edge placement and mid-placement is ≥ 20 percentage points (Δ ≥ 0.20), demonstrating the softmax-dilution effect on the practitioner's own workload.
- **SC-003**: Every compaction event fires inside the half-open interval `[0.55, 0.60)` (i.e. at `usage_fraction >= 0.55` and before capacity exceeds 60%), with zero recorded instances of a session reaching the hard limit without a compaction attempt.
- **SC-004**: Every post-compaction prompt contains every declared critical rule verbatim at both the primacy and latency edges, verified by automated inspection on 100% of compaction events.
