<!--
Sync Impact Report
Version change: 1.3.0 → 2.0.0
Bump rationale: MAJOR — workshop reframed as a concept-first cert-prep
study. Removed: Principle V (Test-First Kata Delivery) and the entire
FDD/IIKit scaffolding (testify, tasks, plan-by-feature, assertion-integrity
hashes, .feature files). Simplified: Principle VIII (Mandatory Documentation)
now requires a single Jupyter notebook per kata as the deliverable, no
duplicated README. Removed Kata Completion Standards items tied to TDD
and dual docs.
Modified principles: VIII rewritten; V removed; numbering preserved by
gapping (formerly "V" left empty intentionally to keep stable references
in any external citation).
Removed sections: TDD references in Development Workflow, "Pre-Commit
Hook Enforcement" (kept advisory only), assertion-integrity language.
Follow-up TODOs: none required by this version; per-kata notebooks become
the next unit of work.
-->

# ia-claude Constitution

This workshop trains practitioners for the **Claude Certified Architect**
credential. It is concept-first: each kata's deliverable is **one detailed
Jupyter notebook** that demonstrates the idea, the anti-pattern, and the
argument the practitioner would make in the certification exam. There is
no TDD, no unit-test gate, no FDD multi-artifact ladder.

## Core Principles

### I. Determinism Over Probability (NON-NEGOTIABLE)

Agent control flow MUST be driven by structured API signals, never by
probabilistic text. Loop termination, tool dispatch, and escalation
decisions MUST key off typed metadata (e.g. `stop_reason`, structured
tool_use blocks, hook verdicts), not regex searches over generated prose.

### II. Schema-Enforced Boundaries (NON-NEGOTIABLE)

Every tool input, tool output, subagent payload, and inter-agent handoff
MUST be validated against a declared schema. Required fields MUST be truly
required; optional fields MUST use nullable unions instead of defaulting to
empty strings. Enumerations MUST include an explicit escape value
(`other`, `unclear`) paired with a details field.

### III. Context Economy

Prompt construction MUST favor stable-prefix / dynamic-suffix ordering so
prefix caches hold across turns. Hard guardrails MUST sit at the extreme
edges of the window. When working memory exceeds ~50% capacity, the agent
MUST compact or externalize discoveries to a durable scratchpad before
continuing.

### IV. Subagent Isolation

Coordinator → subagent orchestration MUST follow hub-and-spoke: the
coordinator passes only the minimum payload a subagent needs and receives
only a typed JSON summary in return. Shared or inherited conversational
memory between agents is forbidden.

### V. *(reserved)*

Intentionally vacated. Earlier revisions of this Constitution mandated
TDD-style kata delivery. The workshop has since been reframed as concept
study; the slot is preserved so external references to "Principle V" do
not silently re-bind to a different rule. Do not re-use this number.

### VI. Human-in-the-Loop Escalation

Any action that is destructive, irreversible, policy-breaching, or exceeds
a declared operational limit MUST suspend agentic generation and emit a
typed escalation payload (summary, actions_taken, escalation_reason).
Exploratory work on unfamiliar code MUST default to read-only planning
before direct execution is authorized.

### VII. Provenance & Self-Audit

Factual claims extracted from sources MUST preserve a machine-readable
link to their origin (claim, source identifier, source name, date). When
two sources disagree, the agent MUST record both under an explicit
conflict marker and delegate resolution. Numeric outputs computed by the
agent MUST be cross-checked against any stated value in the source and
flagged on mismatch.

### VIII. Notebook-as-Deliverable (NON-NEGOTIABLE)

Each kata's single deliverable is a Jupyter notebook at
`katas/kata_NNN_<slug>/notebook.ipynb`. The notebook MUST include:

1. **Concept** — restate the spec's idea in the practitioner's words.
2. **Why it matters** — the failure mode the kata defends against.
3. **Worked example** — runnable code (live API calls allowed, mocked
   responses allowed) demonstrating the deterministic behavior.
4. **Anti-pattern demo** — a side-by-side cell that reproduces the wrong
   approach so the contrast is explicit.
5. **Certification argument** — bullet points the practitioner would say
   aloud to defend the design choice in the certification exam.
6. **Self-check** — answers to the spec's auto-evaluation questions.

No separate `README.md`, no `.feature` file, no `tasks.md`, no schema
contract directory. The notebook is the documentation. A kata is "done"
when its notebook executes top-to-bottom and covers the six sections
above. Stale or empty notebooks block consideration of the kata as
complete.

## Kata Completion Standards

A kata is DONE when:

1. `specs/<NNN-slug>/spec.md` exists (planning artifact, already in repo).
2. `katas/kata_NNN_<slug>/notebook.ipynb` exists, executes top-to-bottom
   without manual edits, and includes the six sections required by
   Principle VIII.
3. The notebook demonstrates the anti-pattern explicitly, not only by
   description.

There is no requirement for unit tests, BDD scenarios, assertion-integrity
hashes, or coverage thresholds.

## Development Workflow

- Per kata: read `specs/<NNN-slug>/spec.md`, then build
  `katas/kata_NNN_<slug>/notebook.ipynb`. That is the entire workflow.
- Order is flexible. Katas may be tackled in any sequence; recommended
  order is the numbered one because later katas reference patterns from
  earlier ones (see `specs/README.md`).
- Live API runs are encouraged; cache responses if cost matters.
- Long investigations may keep a personal scratchpad outside the kata
  notebook (Kata 18 itself teaches this pattern).
- Code review is optional. The notebook is the audit surface.

## Integrity (Advisory)

Pre-commit hooks and CI gates are no longer mandated. If a previous
revision installed the IIKit pre-commit hook, it MAY remain installed but
it has no required artifacts to verify. Contributors who hit a hook
failure may safely uninstall it (`rm .git/hooks/pre-commit`) — this is
no longer a Constitution violation.

## Governance

This Constitution supersedes earlier documents within the repository.
Amendments require an explicit PR that bumps `Version` and `Last Amended`.
Versioning is semantic: MAJOR for principle removal/redefinition, MINOR
for added principles or materially expanded sections, PATCH for
clarifications.

**Version**: 2.0.0 | **Ratified**: 2026-04-23 | **Last Amended**: 2026-04-27
