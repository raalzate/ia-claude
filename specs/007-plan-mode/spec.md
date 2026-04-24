# Feature Specification: Safe Exploration via Plan Mode

**Feature Branch**: `007-plan-mode`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 7 — Prevent destructive modifications to unfamiliar codebases during massive refactorings by enforcing a read-only exploration (Plan Mode) before any write. The agent must compile findings and a proposed architecture into a markdown document, obtain explicit human approval, and only then transition into Direct Execution."

## Clarifications

### 2026-04-24 (phase-06 analyze)

- **"Small, low-risk task" classifier threshold (F-001)**: A request qualifies for the Plan Mode bypass iff it (a) targets exactly one file, (b) introduces no new cross-package imports, and (c) does not modify any file declared under a governance path (`CONSTITUTION.md`, `CLAUDE.md`, `.tessl/**`, `.claude/**`). Anything failing any of the three tests enters full Plan Mode. The classifier is deterministic and lives in `session.classify_request` (tasks T025).
- **FR-004 rename/move scope semantics (F-003)**: A rename or move is treated as editing the destination path — the destination MUST appear in `plan.affected_files` for the operation to proceed; source deletion is an additional affected-file entry. Directory-level `affected_files` entries apply to every file under that directory prefix at the time the plan is approved. Documented in README per T064.
- **@FR-007 dedicated scenario (F-002)**: DEFERRED — FR-007 is indirectly tagged via @TS-009 today; adding a dedicated scenario requires re-running `/iikit-04-testify` (cannot hand-edit `.feature` files per assertion-integrity rule). Coverage is acceptable as-is.

## User Stories *(mandatory)*

### User Story 1 - Large Refactor Triggers a Read-Only Plan Document (Priority: P1)

A practitioner issues an extensive refactor request (e.g., "migrate auth from JWT to session cookies across 20 files"). The agent recognizes the scope, enters Plan Mode, and uses only read, search, and glob capabilities to analyze the codebase. It compiles affected files, dependencies, risks, and a proposed migration sequence into a markdown plan document, then stops and requests human review.

**Why this priority**: This is the primary defense against destructive modifications on unfamiliar codebases. Without a gating plan, the agent may apply broad, incorrect edits that are expensive to unwind. It directly operationalizes Constitution Principle VI (Human-in-the-Loop Escalation) for the highest-risk class of tasks.

**Independent Test**: Submit a refactor request that touches multiple files. Verify that the agent produces a markdown plan document, performs zero write operations during the session, and explicitly waits for human approval before proceeding.

**Acceptance Scenarios**:

1. **Given** the agent receives a refactor request spanning multiple files, **When** the session begins, **Then** the agent enters Plan Mode and only invokes read/search/glob capabilities.
2. **Given** the agent is in Plan Mode, **When** it finishes analysis, **Then** it produces a markdown plan document containing affected files, risks, and ordered migration steps, and halts pending human approval.

---

### User Story 2 - Direct Writes During Plan Mode Are Blocked (Priority: P2)

A practitioner (or an over-eager agent path) attempts to invoke a write, edit, or delete capability while the session is still in Plan Mode. The system blocks the attempt, records the event, and reminds the operator that a reviewed plan and explicit approval are required before Direct Execution.

**Why this priority**: This story is the anti-pattern defense: it prevents jumping straight to edits on an unfamiliar codebase. Without enforcement, Plan Mode becomes advisory only and provides no real safety.

**Independent Test**: Force the agent into Plan Mode, attempt a write/edit/delete tool call, and verify the call is blocked, no file is modified, and the block event is logged.

**Acceptance Scenarios**:

1. **Given** the session is in Plan Mode, **When** any write-class capability is invoked, **Then** the attempt is refused and no file on disk is modified.
2. **Given** a blocked write attempt, **When** the refusal occurs, **Then** the event is logged with the attempted target and the current mode.

---

### User Story 3 - Approved Plan Unlocks Direct Execution (Priority: P3)

After reviewing the plan document, the practitioner approves it. The agent transitions to Direct Execution and applies the changes in the order described by the approved plan. If during execution the scope must change beyond the approved plan, the agent stops and requests a new approval.

**Why this priority**: Enables the refactor to actually complete once safety has been established. It also closes the loop on traceability: every applied change maps back to an approved plan.

**Independent Test**: Provide an approval signal after a plan has been produced, then verify the agent applies only the changes described in the plan and logs the Plan to Execute transition.

**Acceptance Scenarios**:

1. **Given** a plan document has been produced and approved, **When** the agent transitions to Direct Execution, **Then** it applies changes consistent with the approved plan and logs the transition.
2. **Given** the agent is executing, **When** it detects a scope change not covered by the approved plan, **Then** it halts execution and requests a new approval.

---

### Edge Cases

- The agent is asked a small, low-risk task (e.g., fix a typo in a single file) that does not warrant Plan Mode — the system should allow a lightweight path without mandating a full plan document, while still respecting the write-gate policy.
- The human edits the plan document after producing it but before approving — the agent must execute against the edited, approved version, not the originally generated one.
- Plan Mode analysis concludes the refactor is infeasible (e.g., missing dependencies, conflicting constraints) — the agent records the infeasibility in the plan and does not transition to Direct Execution.
- Approval is revoked or the execution session is interrupted mid-way — the agent must stop and avoid leaving the codebase in a partially migrated state without explicit operator direction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST gate Direct Execution behind an explicit human approval of a Plan Document.
- **FR-002**: System MUST prevent any write, edit, or delete capability from executing while the session is in Plan Mode.
- **FR-003**: System MUST produce a markdown Plan Document covering at minimum: affected files, identified risks, and ordered migration steps.
- **FR-004**: System MUST detect scope changes during Direct Execution and stop to request a new approval before continuing outside the approved plan.
- **FR-005**: System MUST log every Plan-to-Execute transition, including the approved Plan Document identifier and the approving actor.
- **FR-006**: System MUST allow read, search, and glob capabilities during Plan Mode to enable dependency analysis.
- **FR-007**: System MUST record blocked write attempts occurring during Plan Mode with mode, target, and timestamp.

### Key Entities

- **Refactor Request**: The practitioner's description of the intended change, including scope signals (files, systems, breadth) used to decide whether Plan Mode is required.
- **Plan Document**: A markdown artifact enumerating affected files, risks, migration steps, and open questions; it is the sole unit of human review.
- **Human Approval Event**: An explicit, attributable signal that a specific Plan Document is authorized for Direct Execution.
- **Execution Session**: The bounded activity of applying changes under an approved Plan Document, with a start, an end, and a log of transitions and blocked attempts.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 writes observed during Plan Mode across all runs of the test corpus.
- **SC-002**: 100% of executions are traceable to an approved Plan Document via logged Plan-to-Execute transitions.
- **SC-003**: The Plan Document lists all affected files for every scenario in the tested corpus (completeness = 100%).
- **SC-004**: Scope-change detection rate equals 100% on the injected scope-creep test set, with the agent halting for re-approval in every case.
