# Phase 0 Research: Safe Exploration via Plan Mode

## Decisions

### D-001 — Enforce Plan Mode via SDK tool-set swap, not a runtime policy

- **Decision**: The agent loop passes a different `tools=[...]` array to
  `anthropic.Anthropic().messages.create(...)` depending on `SessionMode`.
  In `"plan"` mode only `ReadOnlyTools = {read_file, grep, glob}` are
  registered; in `"execute"` mode the loop adds `WriteTools =
  {edit_file, write_file}`.
- **Rationale**: A policy layer that says "don't call write tools in plan
  mode" is advisory — the model can still emit the `tool_use` block and the
  policy must then refuse it, which is an extra, bug-prone step. Not
  registering the write tools at all means the SDK never advertises them to
  the model; the surface is closed structurally. This also makes SC-001 ("0
  writes during plan mode") trivially auditable via a lint test that
  inspects the `tools` kwarg on the recorded request.
- **Alternatives considered**:
  - *Single unified tool registry + server-side refusal handler.* Rejected:
    re-introduces the exact anti-pattern (FR-002) the kata defends against.
  - *Model-side instruction ("you are in plan mode, do not write").*
    Rejected outright per Constitution Principle I — prose instructions are
    probabilistic, structural gates are deterministic.

### D-002 — Pydantic v2 for every structured boundary in this kata

- **Decision**: `PlanDocument`, `HumanApprovalEvent`,
  `SessionModeTransition`, and `ScopeChangeEvent` are pydantic v2 models.
  Each exports a JSON schema under `contracts/` with `$id:
  "https://ia-claude.local/schemas/kata-007/<name>.schema.json"`.
- **Rationale**: Constitution Principle II (NON-NEGOTIABLE). Required
  fields are actually required (`affected_files`, `risks`,
  `migration_steps`, `plan_hash`, `approved_by`, `approved_at`). Optional
  lists (`out_of_scope`, `open_questions`) are nullable lists, not
  empty-string defaults. Mode enums (`plan` / `execute`) are exhaustive —
  no "other" escape because the state machine is total.
- **Alternatives considered**:
  - *Dataclasses + manual validation.* Rejected: duplicates pydantic work,
    drifts from the workshop-wide baseline (Kata 001 D-002).
  - *Plain dicts + JSON-schema library at the boundary.* Rejected: not
    ergonomic for in-code construction and gives weaker IDE affordances.

### D-003 — `plan_hash` = sha256 of the rendered markdown, not of the model

- **Decision**: `plan_hash` is `sha256(plan.to_markdown().encode("utf-8")).
  hexdigest()`. The transition verifier recomputes the hash from the
  *current on-disk markdown* and compares it to the
  `HumanApprovalEvent.plan_hash`; a mismatch refuses the transition.
- **Rationale**: The spec's edge case explicitly says *"the human edits the
  plan document after producing it but before approving — the agent must
  execute against the edited, approved version, not the originally
  generated one."* Hashing the on-disk markdown means the approval binds
  to exactly what the human saw. Hashing the in-memory pydantic object
  would miss human edits entirely. Hashing the markdown (not a
  canonicalised JSON) also lets the human edit in place with any editor.
- **Alternatives considered**:
  - *Hash the pydantic model's `model_dump_json`.* Rejected: defeats the
    "human edits the plan" edge case.
  - *Merkle over individual sections.* Rejected as overkill; a single
    sha256 is sufficient and the failure mode is "re-approve", not
    "approve 7 of 8 sections".

### D-004 — Pre-dispatch scope-change check against `plan.affected_files`

- **Decision**: Before dispatching any `edit_file` / `write_file`
  `tool_use`, the execute-mode handler asserts the target path is in
  `plan.affected_files`. On mismatch, the session emits a
  `ScopeChangeEvent`, halts the loop, and transitions back to plan mode,
  requiring a new approval before any further writes.
- **Rationale**: Catching scope creep *after* the write would violate the
  spec; the check must be pre-dispatch. Keying off the typed list (not a
  free-text "files you mentioned") keeps this deterministic (Principle I)
  and makes SC-004 a simple set-membership assertion across the injection
  fixture.
- **Alternatives considered**:
  - *Post-hoc diff review.* Rejected: allows the destructive act the kata
    exists to prevent.
  - *Tool-side allow-list injection.* Rejected: couples the tool to the
    plan object; cleaner to keep scope enforcement in the session loop.

### D-005 — Recorded fixtures + `LIVE_API=1` gate (workshop-wide baseline)

- **Decision**: Eight recorded JSON fixtures under
  `tests/katas/007_plan_mode/fixtures/` cover the happy path, every edge
  case in the spec, and both anti-patterns (write-in-plan, scope-creep).
  Live SDK calls require `LIVE_API=1` and are excluded from CI.
- **Rationale**: Determinism + offline reproducibility, matching Kata 001
  D-004. The tests verify control flow over typed signals (mode, plan_hash
  equality, path membership, tool-registration contents), not model prose.
- **Alternatives considered**:
  - *VCR.py cassettes.* Rejected as overkill; plain JSON + stub client is
    clearer teaching code.
  - *Mock the SDK.* Rejected: couples tests to SDK internals rather than
    to the observable `tools=[...]` + `tool_use` contract.

### D-006 — Small-refactor bypass is a first-class fixture, not a code path hack

- **Decision**: The spec's edge case — "a small, low-risk task does not
  warrant Plan Mode" — is implemented by a `ScopeClassifier` that returns
  `"small"` or `"large"` based on the count of files a preflight `grep`
  matches. `"small"` skips plan-mode *document production* but STILL runs
  through the same execute-mode write-gate (write tools are registered
  only after the classifier returns `small` OR an approval is present).
- **Rationale**: The edge case says the write-gate policy still applies.
  Keeping the single write-registration code path means SC-001 holds even
  for the small-refactor path; the bypass only skips the markdown artifact
  and the approval round-trip.
- **Alternatives considered**:
  - *Two separate agent loops (small vs large).* Rejected: doubles the
    surface area and the lint tests.
  - *Hard threshold baked into the agent prompt.* Rejected: prose-based
    branching, Principle I violation.

## Tessl Discovery Note

Checked the Tessl registry for reusable tiles covering "plan mode", "human
approval gating", or "read-only agent sessions" at time of writing. No tile
in the `tessl-labs` namespace currently targets this concern at the level
the kata needs — `intent-integrity-kit` itself is the closest match but
operates at the governance-artifact layer (spec/plan/tasks), not the
runtime agent layer. Revisit before `/iikit-07-implement`; if a tile
appears it SHOULD be evaluated against this research file's decisions
before any hand-rolled code is kept.
