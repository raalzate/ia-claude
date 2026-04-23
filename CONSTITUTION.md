<!--
Sync Impact Report
Version change: (none) → 1.0.0
Bump rationale: MAJOR — initial ratification.
Modified principles: n/a (new document).
Added sections: Core Principles (7), Kata Completion Standards, Development Workflow, Integrity, Governance.
Removed sections: none.
Follow-up TODOs:
- Wire `verify-assertion-integrity.sh` into CI (post /iikit-04-testify for first kata).
- Add CI gate running headless architect review on each PR (see Kata 13 derivative).
- Confirm pre-commit hook installed on contributor machines before first implementation phase.
-->

# ia-claude Constitution

## Core Principles

### I. Determinism Over Probability (NON-NEGOTIABLE)

Agent control flow MUST be driven by structured API signals, never by probabilistic text.
Loop termination, tool dispatch, and escalation decisions MUST key off typed metadata
(e.g. `stop_reason`, structured tool_use blocks, hook verdicts), not regex searches over
generated prose. Rationale: pattern-matching on free text silently fails the first time
the model phrases "done" differently; signal-driven code is observable and reproducible.

### II. Schema-Enforced Boundaries (NON-NEGOTIABLE)

Every tool input, tool output, subagent payload, and inter-agent handoff MUST be
validated against a declared schema. Required fields MUST be actually required;
optional fields MUST use nullable/union types instead of defaulting to empty strings.
Enumerations MUST include an explicit escape value (`other`, `unclear`) paired with a
details field. Rationale: schemas prevent silent hallucination and make failures
bisectable; absent schemas push error discovery to production.

### III. Context Economy

Prompt construction MUST favor stable-prefix / dynamic-suffix ordering so prefix caches
hold across turns. Hard guardrails and critical rules MUST sit at the extreme edges of
the window to survive mid-context attention dilution. When working memory exceeds
~50% capacity, the agent MUST compact or externalize discoveries to a durable
scratchpad before continuing. Rationale: the same content can cost 10× or fail to
steer behavior depending on placement.

### IV. Subagent Isolation

Coordinator → subagent orchestration MUST follow hub-and-spoke: the coordinator passes
only the minimum payload a subagent needs and receives only a typed JSON summary in
return. Shared or inherited conversational memory between agents is forbidden.
Rationale: inherited context degrades attention, leaks policy, and makes subagent
failures non-debuggable.

### V. Test-First Kata Delivery (NON-NEGOTIABLE)

TDD is mandatory. For every kata: acceptance scenarios and assertion-integrity hashes
MUST exist and fail before any production code is written; red → green → refactor is
enforced. Test assertions MUST NOT be weakened to turn red green — production code is
changed instead. Rationale: the katas teach deterministic behavior; verifying intent
with executable acceptance criteria is the only credible demonstration.

### VI. Human-in-the-Loop Escalation

Any action that is destructive, irreversible, policy-breaching, or exceeds a declared
operational limit MUST suspend agentic generation and emit a typed escalation payload
(summary, actions_taken, escalation_reason). Exploratory work on unfamiliar code MUST
default to read-only planning before direct execution is authorized. Rationale: silent
autonomy on high-blast-radius actions is the failure mode teams pay for most.

### VII. Provenance & Self-Audit

Factual claims extracted or aggregated from source material MUST preserve a machine-
readable link to their origin (claim, source identifier, source name, date). When two
sources disagree, the agent MUST record both under an explicit conflict marker and
delegate resolution — never pick arbitrarily. Numeric outputs computed by the agent
MUST be cross-checked against any stated value in the source and flagged on mismatch.
Rationale: provenance is the only defense against aggregated hallucination; silent
"pick one" loses audit trail.

## Kata Completion Standards

A kata is DONE only when ALL of the following hold:

1. `spec.md`, `plan.md`, `tasks.md`, and a `.feature` acceptance file exist for it.
2. Acceptance scenarios cover both the stated objective AND the stated anti-pattern.
3. An automated evaluation harness demonstrates the objective is met via signal-level
   assertions (schema conformance, `stop_reason` path, hook verdict, cache-hit metric,
   provenance field presence) — not via string matching over model output.
4. Anti-pattern tests exist and fail closed when the anti-pattern behavior is
   reintroduced.
5. Assertion-integrity hashes in `.specify/context.json` match the locked test set.
6. A short reflection note records the observed failure mode the kata was designed to
   prevent.

## Development Workflow

- Workflow order is fixed: `/iikit-core init` → `/iikit-00-constitution` →
  `/iikit-01-specify` → `/iikit-clarify` (if needed) → `/iikit-02-plan` →
  `/iikit-03-checklist` → `/iikit-04-testify` → `/iikit-05-tasks` →
  `/iikit-07-implement`. Skipping is forbidden; phase-gating scripts MUST pass before
  the next phase.
- Artifact ownership is strict: governance → Constitution; WHAT/WHY → spec; HOW →
  plan; task breakdown → tasks; executable acceptance → `.feature` files. Content
  placed in the wrong artifact MUST be relocated, not duplicated.
- Code review is mandatory and SHOULD include an automated deterministic reviewer
  invoked headlessly (JSON-schema-validated output) on every PR. Human review remains
  the final gate for merge.
- Long-running investigations MUST persist discoveries to a scratchpad file
  referenced from the feature's `plan.md` so context compaction is survivable.
- Experiments that would be prohibitive in real time MAY be run via asynchronous
  batch processing when results are not user-blocking.

## Integrity

### Pre-Commit Hook Enforcement (NON-NEGOTIABLE)

Pre-commit hooks are a critical integrity gate. The following are prohibited:

- **NEVER** use `git commit --no-verify` or `git commit -n` to bypass hooks
- **NEVER** delete, modify, or disable files in `.git/hooks/`
- **NEVER** use git plumbing commands (`git commit-tree`, `git mktree`) to circumvent hooks
- If a pre-commit hook blocks your commit, **fix the root cause** — do not work around the hook
- For assertion integrity failures: re-run `/iikit-04-testify` to regenerate hashes

**CI enforcement recommended**: Add `verify-assertion-integrity.sh` to your CI pipeline
for server-side verification that cannot be bypassed. See the CI integration reference
for setup instructions.

## Governance

This Constitution supersedes all other conventions, style guides, and informal
practices within the repository. When any guidance conflicts with these principles,
this document wins and the conflicting guidance MUST be updated or removed.

- Amendments require an explicit PR that: (a) states the principle change and its
  rationale, (b) updates this file's `Version` and `Last Amended` fields, (c) lists
  downstream artifacts requiring realignment (specs, plans, tasks, features), and
  (d) receives human approval before merge.
- Versioning is semantic: MAJOR for principle removal/redefinition, MINOR for added
  principles or materially expanded sections, PATCH for clarifications and typos.
- Every PR description MUST include a compliance line asserting which principles were
  touched and that all touched artifacts remain consistent.
- Complexity that appears to violate a principle MUST be justified in the PR body
  with a named exception scope and an expiration condition. Unjustified violations
  block merge.
- Runtime development guidance for agents and contributors lives in `AGENTS.md` and
  the `.tessl/RULES.md` chain; those files MUST NOT contradict this Constitution.

**Version**: 1.0.0 | **Ratified**: 2026-04-23 | **Last Amended**: 2026-04-23
