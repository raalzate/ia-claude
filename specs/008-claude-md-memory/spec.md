# Feature Specification: Hierarchical Memory Orchestration in CLAUDE.md

**Feature Branch**: `008-claude-md-memory`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 8 — Establish universal team coding conventions within a repository (project-scope CLAUDE.md with modular `@path` references) without conflicting with individual user-level preferences (`~/.claude/CLAUDE.md`)."

## User Stories *(mandatory)*

### User Story 1 - Zero-Setup Team Conventions on Fresh Clone (Priority: P1)

A practitioner clones the repository for the first time and starts an agent session. The agent automatically loads the repo-level memory file (`.claude/CLAUDE.md` or root-level `CLAUDE.md`) and adopts the team's coding conventions without any manual configuration, environment variables, or per-user setup steps.

**Why this priority**: This is the core value of hierarchical memory — team conventions must travel with the code so every contributor (and every agent) starts from the same baseline. Without this, the feature delivers no team-level value.

**Independent Test**: Delete the working copy, re-clone the repository into a clean directory, start an agent session, and ask the agent to perform a task governed by a team convention (e.g., "use pnpm instead of npm"). The agent must follow the convention without being reminded.

**Acceptance Scenarios**:

1. **Given** a fresh clone of the repository and no user-level memory overriding team rules, **When** the practitioner starts an agent session in the repo root, **Then** the agent loads the project memory file and treats its contents as authoritative for project work.
2. **Given** a project memory file that references an external manual via `@./standards/coding-style.md`, **When** the agent starts up, **Then** the referenced manual's content is resolved and available to the agent without the practitioner opening it manually.

---

### User Story 2 - Team Rules Win Over Personal Preferences on Project Tasks (Priority: P2)

A practitioner keeps personal preferences (preferred language, formatting quirks, shortcuts) in `~/.claude/CLAUDE.md`. When those personal preferences conflict with a team convention declared in the repo's project memory, the agent follows the team convention while working inside the project. This is the explicit anti-pattern defense: personal-scope files must NOT pollute team behavior.

**Why this priority**: Without precedence rules, a single developer's personal file can silently alter how the agent behaves on shared code, producing inconsistent output across the team. P2 because P1 must exist before precedence is meaningful.

**Independent Test**: Add a personal rule to `~/.claude/CLAUDE.md` that contradicts a team rule in `.claude/CLAUDE.md` (e.g., personal says "use tabs", team says "use spaces"). Ask the agent to produce code in the project. The output must honor the team rule.

**Acceptance Scenarios**:

1. **Given** a team rule "use pnpm" in project memory and a personal rule "use npm" in user memory, **When** the agent performs a project task requiring a package manager, **Then** the agent uses pnpm.
2. **Given** a personal preference that does not conflict with any team rule, **When** the agent performs a task where only the personal preference applies, **Then** the personal preference is respected.

---

### User Story 3 - Editing a Referenced Manual Updates Agent Behavior Without Touching CLAUDE.md (Priority: P3)

A practitioner edits an external manual referenced from the project memory file (e.g., `@./standards/coding-style.md`). The next agent session reflects the updated manual without any edit to `CLAUDE.md` itself. This validates that the modular `@path` structure is a live reference, not a snapshot.

**Why this priority**: Modularity is the practical win — it keeps the top-level memory file small and lets domain manuals evolve independently. P3 because P1 and P2 establish the loading and precedence behavior that this story depends on.

**Independent Test**: Edit `./standards/coding-style.md` to add a new rule. Start a fresh agent session. Ask the agent to perform a task governed by the new rule. The new rule is honored without any change to `CLAUDE.md`.

**Acceptance Scenarios**:

1. **Given** a project memory file containing `@./standards/coding-style.md` and an updated version of that manual, **When** the agent starts a new session, **Then** the new rules take effect.
2. **Given** an `@path` reference is removed from `CLAUDE.md`, **When** the agent starts a new session, **Then** rules that only lived in the dereferenced manual no longer apply.

---

### Edge Cases

- What happens when a referenced `@path` target is missing (file deleted, wrong path, typo)? The system MUST fail loud with an explicit diagnostic, not silently drop the rules.
- What happens when `@path` references form a circular chain (A references B, B references A)? Resolution must terminate and report the cycle rather than loop indefinitely.
- What happens when a personal rule in `~/.claude/CLAUDE.md` and a team rule in project memory directly disagree? Project memory wins for project work; the conflict SHOULD be surfaced so the practitioner can reconcile intentionally.
- What happens when the aggregated memory (project file plus all resolved `@path` manuals) grows very large and begins to strain the agent's context budget (Constitution III — Context Economy)? The system must respect a declared size budget and flag overruns.
- What happens when a practitioner accidentally places a team-wide convention in `~/.claude/CLAUDE.md` instead of the project file? The convention fails to propagate to teammates — this is the documented anti-pattern and must be discoverable in the checklist review.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST load project-level memory from a repo-committed file (`.claude/CLAUDE.md` or repo-root `CLAUDE.md`) at agent startup without any per-user configuration.
- **FR-002**: System MUST support `@path` references from the project memory file to external manuals (e.g., `@./standards/coding-style.md`) and resolve their contents as part of the effective memory.
- **FR-003**: System MUST keep personal memory separate and user-scoped at `~/.claude/CLAUDE.md` so that personal rules do not enter version control or alter teammates' agent behavior.
- **FR-004**: System MUST fail loud with an explicit diagnostic when an `@path` target is missing, unreadable, or produces a resolution cycle — silent degradation is prohibited.
- **FR-005**: System MUST make effective memory deterministic across fresh clones — given the same commit SHA, every developer's agent loads the same project rules in the same resolution order.
- **FR-006**: System MUST define and document a memory resolution order in which project-level rules take precedence over personal rules for project tasks.
- **FR-007**: System MUST keep the top-level `CLAUDE.md` within a declared size budget, relying on `@path` modularization rather than inline bloat.

### Key Entities

- **Team Memory File**: The repo-committed file (`.claude/CLAUDE.md` or root `CLAUDE.md`) that encodes universal team coding conventions. Travels with the code via version control.
- **Personal Memory File**: The user-scoped file at `~/.claude/CLAUDE.md` that encodes an individual developer's preferences. Never committed; never propagated.
- **Referenced Manual**: An external markdown file (e.g., `./standards/coding-style.md`) pulled into the effective memory via an `@path` reference from the Team Memory File.
- **Memory Resolution Order**: The deterministic precedence chain — project-scope wins over user-scope on project tasks; `@path` references are resolved in the order they are declared; cycles and missing targets abort loading with a diagnostic.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fresh clone yields identical agent behavior across developers — 100% reproducibility on a defined test prompt set, with no developer-specific drift attributable to memory loading.
- **SC-002**: Personal rules never override declared team rules on project tasks — 0 conflicts pass through to agent output in the conflict test matrix.
- **SC-003**: The modular `@path` structure keeps `CLAUDE.md` under a declared size budget (top-level file size measured and compared to the budget on every commit).
- **SC-004**: A missing `@path` target triggers an explicit diagnostic in 100% of cases — silent degradation is never observed in the failure test set.
