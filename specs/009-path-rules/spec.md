# Feature Specification: Path-Scoped Conditional Rules

**Feature Branch**: `009-path-rules`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 9 — Path-Scoped Conditional Rules: save context-window space by loading programming heuristics only when the agent edits files matching a defined pattern."

## User Stories *(mandatory)*

### User Story 1 - Testing rules auto-inject on test edits (Priority: P1)

A practitioner opens the workshop repository and edits a file matching the testing pattern (e.g. `**/*.test.tsx`). The agent automatically loads only the rules declared in `.claude/rules/testing.md` — which cover conventions like `describe/it` block structure and data-factory usage — so the practitioner receives targeted guidance without paying token cost for unrelated rule files.

**Why this priority**: This is the headline behavior of the kata. Without automatic injection on matching edits, there is no value delivered — the whole feature exists to make the right rules appear at the right moment.

**Independent Test**: Can be fully tested by (a) creating `.claude/rules/testing.md` with a `paths` frontmatter entry for `**/*.test.tsx`, (b) asking the agent to edit a `.test.tsx` file, and (c) confirming the testing rules are present in the active context and that no non-matching rule files were loaded.

**Acceptance Scenarios**:

1. **Given** `.claude/rules/testing.md` declares `paths: ["**/*.test.tsx"]` and the file is otherwise valid, **When** the practitioner edits `src/components/Button.test.tsx`, **Then** the testing rules are injected into the active turn and an audit entry records `testing.md` as activated.
2. **Given** multiple rule files exist but only one matches, **When** the practitioner edits a single matching file, **Then** only the matching rule file is injected and the audit log lists exactly that one activation.

---

### User Story 2 - No rule tokens spent on unrelated edits (Priority: P2)

A practitioner edits a source file that is not matched by any rule file's path pattern. The agent performs the edit without loading any rule file — defending against the anti-pattern of always-on rule loading that wastes tokens on every turn regardless of relevance.

**Why this priority**: This is the context-economy payoff (Constitution principle III). Without this guarantee, the feature collapses into the very anti-pattern it is meant to prevent.

**Independent Test**: Can be fully tested by editing a file that matches no declared pattern and verifying (via the activation audit log) that zero rule files were injected and that token usage for that turn is equivalent to a baseline turn with no `.claude/rules/` directory present.

**Acceptance Scenarios**:

1. **Given** `.claude/rules/` contains rule files but none declare a pattern matching `README.md`, **When** the practitioner edits `README.md`, **Then** no rule file is injected and the audit log shows zero activations for that turn.
2. **Given** the practitioner performs a read-only operation that touches no file, **When** the turn completes, **Then** no rule file is injected.

---

### User Story 3 - New rule file activates only on matching edits (Priority: P3)

A practitioner adds a new rule file (e.g. `.claude/rules/api-conventions.md`) with a new path pattern (e.g. `paths: ["src/api/**/*.ts"]`). The file begins activating automatically on edits to matching paths and remains dormant on all other edits — no code change, no agent restart, no CLAUDE.md edit required.

**Why this priority**: This proves the mechanism is extensible and governs itself by frontmatter declarations, not by hard-coded agent logic. It is P3 because P1 and P2 already constitute a usable MVP.

**Independent Test**: Can be fully tested by adding a new rule file with a distinct pattern, editing a matching file and a non-matching file in sequence, and confirming the activation audit log reflects one activation and zero activations respectively.

**Acceptance Scenarios**:

1. **Given** a newly added `.claude/rules/api-conventions.md` with `paths: ["src/api/**/*.ts"]`, **When** the practitioner edits `src/api/users.ts`, **Then** `api-conventions.md` is injected.
2. **Given** the same new rule file, **When** the practitioner edits `src/components/Button.tsx`, **Then** `api-conventions.md` is NOT injected.

---

### Edge Cases

- **Overlapping patterns**: Two rule files each declare a pattern that matches the same edited file. Precedence resolution must be deterministic (see FR-004) so both practitioners and auditors get a predictable outcome.
- **Pattern matches nothing**: A rule file declares a pattern that matches no file in the repository. The file is inert — it is loaded into neither the current turn nor any future turn until a matching file is edited.
- **Invalid frontmatter**: A rule file has malformed YAML, a missing `paths` key, or a non-list `paths` value. The system MUST surface an explicit load-time error rather than silently dropping the file (anti-pattern: silent skip hides misconfiguration from the practitioner).
- **Very large rule file**: A single matching rule file is large enough to dominate the context budget for a turn. The activation audit log must still report it so the practitioner can decide to split the file or narrow its pattern.
- **File touched by tool but not edited**: Read-only tool calls that reference a path matching a pattern should not trigger rule injection, because the kata scopes activation to edits.
- **Multiple matching files in one turn**: The agent edits several files in one turn, each matching a different rule file. All corresponding rule files activate, deduplicated, and the audit log lists every one.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST load rule files from `.claude/rules/` conditionally, injecting a rule file into a turn only when at least one file edited during that turn matches a `paths` glob declared in that rule file's YAML frontmatter.
- **FR-002**: The system MUST NOT inject any rule file into turns where no edited file matches any declared pattern (defends against the always-on anti-pattern that wastes tokens).
- **FR-003**: The system MUST validate each rule file's frontmatter at load time, requiring a `paths` key whose value is a non-empty list of glob strings; invalid frontmatter MUST produce an explicit error message that identifies the offending file and the failure reason.
- **FR-004**: The system MUST deterministically resolve pattern overlaps using a documented precedence order (e.g. alphabetical filename ascending, or an explicit `priority` frontmatter field when declared) so two runs over the same edits produce the same activation set in the same order.
- **FR-005**: The system MUST record, per turn, which rule files activated and which edited path triggered each activation, producing an auditable activation log that the practitioner can inspect.
- **FR-006**: The system MUST treat rule files whose patterns match nothing in the current turn as inert — they MUST NOT contribute any tokens to that turn's context.
- **FR-007**: The system MUST restrict domain-specific rules to `.claude/rules/` path-scoped files; domain-specific heuristics MUST NOT be placed in the global `CLAUDE.md` (defends against the anti-pattern of globally broadcasting narrow rules).

### Key Entities

- **Rule File**: A markdown file in `.claude/rules/` containing YAML frontmatter and rule content. Attributes: filename, frontmatter (including `paths` list and optional precedence hint), body.
- **Path Pattern**: A glob string declared inside a Rule File's frontmatter that determines which edited files cause the Rule File to activate. Attributes: glob expression, owning rule file.
- **Active Rule Set**: The deduplicated collection of Rule Files injected into a given turn, produced by matching the turn's edited paths against all declared Path Patterns. Attributes: turn identifier, member rule files, total token footprint.
- **Matching Event**: A record linking one edited path to one Rule File activation within a turn. Attributes: turn identifier, edited path, rule file, pattern that matched.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Token cost for a turn that edits only files unmatched by any rule file is unchanged when new rule files are added to `.claude/rules/` (measured: baseline turn token count equals post-addition turn token count within a small measurement tolerance).
- **SC-002**: 100% of turns that edit at least one file matching a declared pattern result in the correct rule file(s) appearing in the activation audit log (measured against a fixture set of edit scenarios).
- **SC-003**: 100% of rule files with invalid frontmatter produce an explicit, human-readable error at load time — zero instances of silent skip.
- **SC-004**: The rule-activation audit log is complete: for every turn that edits files, the log lists every rule file that activated and the specific path that triggered each activation, with no missing entries across a test suite of representative edit scenarios.
