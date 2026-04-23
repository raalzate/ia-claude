# Phase 0 Research: Softmax Dilution Mitigation

## Decisions

### D-001 — Use the official `anthropic` Python SDK for live compliance measurement

- **Decision**: The compliance harness (`compliance.py`) submits each rendered
  `PromptLayout` to `anthropic.Anthropic().messages.create(...)` N times and
  records one `ComplianceRecord` per trial. The SDK is the sole transport.
- **Rationale**: SC-001 and SC-002 only become evidence when produced against
  the live model on the practitioner's own workload — recorded fixtures are
  insufficient for the *discovery* run of the workshop. Fixtures cover
  regression protection; the live sweep produces the empirical compliance
  table the kata teaches.
- **Alternatives considered**:
  - *Raw HTTP + JSON.* Rejected: reimplements typed response handling for no
    pedagogic value (same rationale as kata 001 D-001).
  - *LangChain / LlamaIndex.* Rejected: abstracts away the structured
    response surface the kata depends on.
  - *Only recorded fixtures, no live sweep.* Rejected: fixtures cannot
    *produce* compliance evidence, they can only reproduce it.

### D-002 — Pydantic v2 models for every structured boundary

- **Decision**: `CriticalRule`, `EdgeRegion`, `PromptLayout`, `CompactionEvent`,
  `ComplianceRecord` are pydantic v2 models. JSON Schema exports live under
  `specs/011-softmax-mitigation/contracts/`. Every ingress / egress boundary
  passes through `model_validate` / `model_dump_json`.
- **Rationale**: Constitution Principle II (Schema-Enforced Boundaries, NN).
  Consistent with kata 001 D-002 — schemas fail loud instead of silently
  accepting malformed payloads.
- **Alternatives considered**:
  - *TypedDict / dataclasses.* Rejected: no runtime enforcement, violates
    Principle II.

### D-003 — Declared compliance target X = 95% for edge placement; Δ = 20 percentage points for mid-burial

- **Decision**: The edge-placement compliance target for US1 is **95%** across
  the adversarial batch. The minimum declared compliance drop Δ between
  `edge_placed` and `mid_buried` layouts for US2 is **20 percentage points**
  absolute (e.g. 95% edge → ≤75% mid qualifies as observable dilution).
- **Rationale**: Published "lost in the middle" studies (Liu et al. 2023;
  Chen et al. 2024 long-context benchmarks) observe 15–40 percentage point
  compliance gaps between edge and mid placement on long-context tasks with
  single-rule guardrails. 95% is a defensible floor for a single hard
  guardrail with both-edge anchoring on a modern Claude model, and 20 points
  is conservatively at the low end of the literature range — it rules out
  noise without being trivially passable. The kata harness parameterises
  both numbers so a practitioner can tighten them if their workload supports
  it.
- **Alternatives considered**:
  - *Target 99%.* Rejected: the point of the kata is to measure, not to
    prescribe a number the workshop audience cannot independently justify on
    their own workload. 99% looks like an SLO rather than an empirical floor.
  - *Δ = 10 points.* Rejected: inside the noise band for N=30 trials; a
    practitioner could pass US2 without actually having demonstrated
    dilution. 20 points provides headroom over Bernoulli-trial noise at the
    declared batch size.
  - *Leave X and Δ as NEEDS CLARIFICATION.* Rejected: Phase-1 artifacts must
    resolve measurable-number unknowns so `/iikit-04-testify` can lock the
    assertions. The numbers are documented here, declared in
    `PromptLayout.compliance_target_pct` and `PromptLayout.min_delta_pct` on
    the pydantic models, and re-asserted in the BDD scenarios.

### D-004 — Proactive compaction threshold = 0.55 (fire-by-0.60 hard ceiling)

- **Decision**: `CompactionTrigger` fires when
  `total_tokens / context_window ≥ 0.55`. It MUST complete before the fraction
  crosses `0.60`. Unit tests assert fire/no-fire on the boundary table
  `[0.49, 0.55, 0.59, 0.60, 0.61]`.
- **Rationale**: The 50–60% band is the value spec.md calls out directly
  (FR-002), and 0.55 is the midpoint — it gives the compactor headroom to
  complete before the 60% ceiling declared in SC-003 while still firing late
  enough that short sessions don't pay for compaction needlessly. The 0.60
  hard ceiling is the point at which measured mid-context attention begins
  to degrade in long-context benchmarks on current-gen models; firing after
  it would leave the next turn operating on an already-diluted prompt.
- **Alternatives considered**:
  - *Fixed 0.50 threshold.* Rejected: too eager; short sessions never reach
    the dilution regime and pay compaction cost for nothing.
  - *Fixed 0.60 threshold.* Rejected: no headroom — a burst on the next turn
    can push usage past 0.60 before compaction completes, which SC-003
    forbids.
  - *Model-provided attention-health signal.* Rejected: no such first-class
    SDK signal exists today; using model output to decide when to compact
    would be a Principle I violation (control flow on probabilistic signal).

### D-005 — Multi-rule priority: declared integer, input-order tie-break

- **Decision**: `CriticalRule.priority` is a required non-negative integer,
  **lower wins** (i.e. priority 0 is placed first). Ties resolve by the rule's
  position in the input list. Placement walks the rule list primacy-first,
  then latency-first, stopping when the next rule would exceed the edge
  region's `budget_tokens`; remaining rules are marked `deferred` on the
  `PromptLayout` and surfaced on the run — never silently dropped.
- **Rationale**: Edge-cases block in spec.md requires a declared ordering
  (not "obvious" ordering) for multi-rule competition. A numeric priority
  plus input-order tie-break is deterministic, reviewable in code review,
  and survives refactors that reorder the input list only for the ties. The
  `deferred` surfacing satisfies FR-004's "rules preserved" logging clause
  even when a rule fails to place.
- **Alternatives considered**:
  - *Alphabetical by rule id.* Rejected: hides the *decision* of which rule
    matters more inside a naming convention; a rename silently changes
    behavior.
  - *First-fit greedy by token length.* Rejected: short rules displace
    important long rules for reasons unrelated to the author's intent.

### D-006 — Compliance scoring via structured probe, not prose matching

- **Decision**: Each `CriticalRule` ships with a `compliance_probe_schema`
  (a JSON Schema) describing a structured JSON object the model is asked to
  emit at the end of its response. The scorer reads that JSON; a valid
  payload with the rule-compliant field is counted `obeyed`, an invalid or
  violating payload is `violated`, a missing payload is `undetermined` and
  surfaced rather than coerced to a pass or a fail.
- **Rationale**: Constitution Principle I. Scoring rule compliance by
  regex-over-prose is precisely the anti-pattern the whole workshop is
  designed to prevent. The AST-lint carried from kata 001
  (`tests/katas/011_softmax_mitigation/lint/test_no_prose_matching.py`) fails
  the build if `re`, `str.find`, or `in` on a text block is reintroduced in
  `compliance.py`.
- **Alternatives considered**:
  - *LLM-judge scoring.* Rejected: replaces one probabilistic signal with
    another; not a legitimate Principle-I defense.
  - *Rule authors writing custom scorers per rule.* Rejected: no declared
    schema means no assertion-integrity hash coverage and no portable
    regression story.

### D-007 — Recorded fixtures for CI + `LIVE_API=1` gate for discovery

- **Decision**: Default `pytest tests/katas/011_softmax_mitigation` runs
  offline against recorded Anthropic responses stored under
  `tests/katas/011_softmax_mitigation/fixtures/`. The live compliance sweep
  is gated behind `LIVE_API=1` and invoked as
  `python -m katas.011_softmax_mitigation.runner --sweep`. This mirrors kata
  001 D-004.
- **Rationale**: CI must be deterministic and quota-free (kata 001 D-004);
  the compliance numbers themselves (SC-001, SC-002) only become credible
  when measured live, so the workshop keeps the two paths explicitly
  separated. Recorded fixtures protect against regression in the builder,
  trigger, and scorer; the live sweep produces the evidence table.
- **Alternatives considered**:
  - *Always live.* Rejected: CI cost and flakiness.
  - *Always offline.* Rejected: produces no compliance evidence.

## Tessl Tiles

`tessl search softmax` and `tessl search context-economy` (run 2026-04-23)
returned no tiles covering the attention-dilution / edge-placement domain.
Closest hits were unrelated (marketing, CRM). **No tiles installed for this
feature.** Follow-up: if a community tile for prompt-composition / context-
budgeting later appears (search terms: `prompt-composer`, `context-economy`,
`long-context-placement`), revisit at kata 012 plan time. No eval scores
recorded.

## Unknowns Carried Forward

None. Every NEEDS CLARIFICATION surfaced in `spec.md` as a declared numeric
placeholder (X%, Δ, the 50–60% compaction band) is resolved here — X = 95%
(D-003), Δ = 20 percentage points (D-003), threshold = 0.55 with 0.60 ceiling
(D-004). These values are recorded on the pydantic models and in the
`.feature` assertions that `/iikit-04-testify` will lock.
