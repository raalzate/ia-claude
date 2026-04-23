# Feature Specification: Adaptive Investigation (Dynamic Decomposition)

**Feature Branch**: `019-adaptive-investigation`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 19 — Enable a coordinator agent to generate an architectural plan on the fly in an unfamiliar domain rather than committing to a rigid upfront plan. The agent must first perform topological mapping (filename-pattern search and regex-search), emit a prioritized plan based on discovered structure, and re-adapt when new information invalidates the current plan — all within a bounded exploration budget."

## User Stories *(mandatory)*

### User Story 1 - Open Directive Triggers Topology-First Planning (Priority: P1)

A practitioner hands the coordinator agent an open, exploratory directive (for example, "Add tests for this legacy codebase") without describing the project's internal structure. The agent must resist the temptation to draft a plan from general priors; instead it first performs a topology mapping pass using filename-pattern search (Glob) and regex-search (Grep) over the workspace, then emits a prioritized plan that references the modules and entry points it actually discovered.

**Why this priority**: This is the core capability of the kata. Without topology-first behavior, every downstream adaptation is meaningless because the initial plan is not grounded in the real codebase. P1 because a single slice delivers the full MVP: an open directive in, a grounded prioritized plan out.

**Independent Test**: Given a fresh unfamiliar codebase and an open directive, the practitioner can verify that (a) topology-mapping tool calls occur before any plan is emitted, and (b) the emitted plan cites concrete discovered artifacts (module names, file groups, entry points). This slice can ship and be demonstrated on its own.

**Acceptance Scenarios**:

1. **Given** an unfamiliar codebase and the directive "Add tests for this legacy codebase", **When** the agent is started, **Then** the first externally observable actions are filename-pattern and regex-search queries over the workspace, and no plan is emitted before those queries complete.
2. **Given** the topology pass has completed and discovered three uncovered modules, **When** the agent emits its plan, **Then** the plan is structured (ordered items with explicit priority) and each high-priority item references at least one concrete discovered module.
3. **Given** the practitioner reviews the emitted plan, **When** they compare it against the discovery log, **Then** every prioritized item traces back to a recorded topology finding.

---

### User Story 2 - Injected Surprise Forces Plan Re-adaptation (Priority: P2)

A practitioner plants an unexpected external dependency inside the codebase (for example, a hidden network client or an uninitialized database driver) that the agent cannot have anticipated from the original directive. As the agent proceeds through its plan and discovers the dependency, it must pause, revise its plan (for example, insert a "mock this dependency first" step), log the trigger, and only then continue. It must not keep executing the stale plan as if nothing happened.

**Why this priority**: Directly defends the first anti-pattern: committing to a rigid plan produced before any exploration. P2 because it presupposes P1's grounded plan exists and now tests whether that plan is actually mutable.

**Independent Test**: The practitioner seeds a known surprise, runs the agent, and checks the plan-revision log for (a) a new revision triggered by the surprise, (b) a concrete new step addressing it, and (c) no continued execution of the now-invalidated prior step.

**Acceptance Scenarios**:

1. **Given** the agent is executing plan step N and has a valid current plan, **When** a previously unknown external dependency is discovered during step N, **Then** the agent halts step N, creates a new plan revision, and records the discovery as the trigger.
2. **Given** a plan revision has been created in response to a surprise, **When** execution resumes, **Then** the next executed step is drawn from the revised plan, not the stale plan.
3. **Given** the surprise specifically requires isolation (for example, an external network call), **When** the revised plan is emitted, **Then** a mocking or isolation step is inserted before any step that would exercise the dependency.

---

### User Story 3 - Bounded Exploration Still Produces a Plan (Priority: P3)

A practitioner caps the agent's exploration budget (wall-clock time, iteration count, or tool-call count) and verifies that the agent still produces a structured, prioritized plan within that budget — even if the topology mapping is incomplete. The agent must not explore indefinitely in pursuit of a "perfect" map; it must converge.

**Why this priority**: Directly defends the second anti-pattern: exploring endlessly without ever producing a structured plan. P3 because it is a safety rail on top of P1 and P2 rather than the primary value driver.

**Independent Test**: The practitioner sets a tight budget on a large codebase, runs the agent, and verifies that (a) the budget was respected, (b) a structured plan was nevertheless emitted, and (c) the plan is explicitly annotated as "budget-limited / partial topology" so downstream consumers understand its confidence level.

**Acceptance Scenarios**:

1. **Given** an exploration budget of B (time, iterations, or tool calls), **When** the agent is run against a codebase too large to fully map within B, **Then** the agent halts exploration at or before B and emits a structured plan.
2. **Given** the agent halted due to budget exhaustion, **When** the plan is inspected, **Then** it carries an explicit "partial topology" or "budget-limited" annotation and a confidence indicator.
3. **Given** any run of the agent, **When** the full transcript is audited, **Then** there is no run in which the agent performs unbounded topology mapping without ever emitting a plan.

---

### Edge Cases

- Codebase is too small for topology mapping to yield meaningful structure (for example, a single file). The agent should still emit a plan, but may legitimately skip most mapping work; it must flag the "trivial topology" case rather than fabricating structure.
- Topology tools (filename-pattern search or regex-search) error out or return no results. The agent must record the tool failure, fall back to a safe default (for example, minimal plan with an explicit "tooling unavailable" trigger), and not proceed as if mapping succeeded.
- Discovered module dependencies form a cycle. The agent must detect the cycle, record it as a trigger, and produce a plan revision that explicitly acknowledges the cycle (for example, pick a cut point rather than silently looping).
- A discovered surprise contradicts the original directive (for example, the "legacy codebase" is actually generated code that should not be tested by hand). The agent must surface the contradiction as a plan-revision trigger and stop, rather than forcing the original directive through.
- The agent produces a plan revision that is functionally identical to the prior revision. The system must either coalesce the duplicate or flag it, to avoid revision-log spam masking real adaptation.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST perform topology mapping (at minimum one filename-pattern query and one regex-search query, or a documented equivalent) before emitting any plan.
- **FR-002**: The agent MUST emit a structured, prioritized plan (ordered items with explicit priority markers), not free-form prose.
- **FR-003**: The agent MUST re-plan when a new discovery invalidates the currently executing step, producing a new plan revision instead of mutating the prior revision in place.
- **FR-004**: The agent MUST enforce an exploration budget (time, iterations, or tool calls) and terminate exploration at or before budget exhaustion.
- **FR-005**: The agent MUST log every plan revision with an explicit trigger reference (the discovery, tool failure, cycle, or budget event that caused the revision).
- **FR-006**: The agent MUST annotate any plan produced under a truncated or incomplete topology pass as "partial" or "budget-limited" with a confidence indicator.
- **FR-007**: The agent MUST, when a discovery contradicts the original directive, halt and surface the contradiction rather than silently continuing.
- **FR-008**: The agent MUST ensure each high-priority plan item traces back to at least one recorded topology finding.

### Key Entities

- **Exploratory Directive**: The open, coarse-grained task the practitioner submits (for example, "Add tests for this legacy codebase"). Has no internal structural knowledge embedded.
- **Topology Map**: The set of facts the agent has learned about the codebase via filename-pattern and regex-search queries. Includes modules, entry points, dependency edges, and observed gaps.
- **Plan Revision**: A versioned, ordered list of prioritized steps. Each revision supersedes the previous one and is immutable once superseded.
- **Trigger Event**: The concrete cause of a plan revision — a new discovery, a tool failure, a detected cycle, a contradiction, or a budget event. Every revision has exactly one primary trigger.
- **Budget**: The bound on exploration (wall-clock, iteration count, or tool-call count). Exhaustion is itself a Trigger Event that forces plan emission.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of runs produce a structured prioritized plan within the configured exploration budget.
- **SC-002**: When a practitioner injects an unexpected external dependency, the agent triggers a plan revision that addresses it in at least the target percentage of runs (target defined per evaluation cohort; minimum acceptable baseline is the rate agreed during kata calibration).
- **SC-003**: 0 runs in which the agent explores without ever emitting a plan (no endless-exploration runs across the evaluation cohort).
- **SC-004**: 100% of plan revisions have a logged trigger that unambiguously identifies the discovery, tool failure, cycle, contradiction, or budget event that caused them.
