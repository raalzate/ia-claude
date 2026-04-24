# Feature Specification: Transactional Memory Preservation via Scratchpad

**Feature Branch**: `018-scratchpad-persistence`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "Kata 18 — Combat the cliff effect of memory loss by externalizing persistent cognitive discoveries from an exploratory agent into a durable, structured scratchpad file that survives `/compact` resets and session boundaries."

## Clarifications

### 2026-04-24 (phase-06 analyze)

- **US2 context-fill trigger**: Pinned the proactive-compaction trigger at `55%` context fill (matches plan.md D-003 and feature TS-008). The earlier "50–60%" narrative band is dropped.
- **FR-005 size cap**: The declared size cap is `MAX_SCRATCHPAD_BYTES = 100_000` bytes (module constant — plan.md §Constraints, task T008). Rotation is emitted when the active file reaches that cap.

## User Stories *(mandatory)*

### User Story 1 - Long Investigation with Incremental Persistence (Priority: P1)

A practitioner launches an exploratory agent to navigate deep routing or architecture logic in an unfamiliar codebase. As the agent uncovers each critical finding (entry points, dependency edges, invariants, suspected bugs), it appends that finding to a declared scratchpad file on disk before continuing. The scratchpad is populated transactionally rather than at the end of the session, so no single context event can erase what was learned.

**Why this priority**: Without durable capture at the moment of discovery, every insight lives only in volatile conversational context. This is the foundational behavior that makes all other scratchpad guarantees possible — if findings are not written out as they occur, nothing downstream can recover them.

**Independent Test**: Run an exploratory investigation for at least three distinct discoveries, terminate the session abruptly, then inspect the scratchpad file. All three findings must be present, each in its declared section, without needing any post-session save step.

**Acceptance Scenarios**:

1. **Given** a fresh investigation session with no existing scratchpad, **When** the agent makes its first critical finding, **Then** the scratchpad file is created with the declared section structure and the finding is written into the correct section.
2. **Given** an active investigation with N prior findings already in the scratchpad, **When** the agent makes a new finding, **Then** the new finding is appended without modifying or reordering existing entries.
3. **Given** an investigation in progress, **When** the session is terminated without any explicit save action, **Then** every finding that was acknowledged before termination is already on disk.

---

### User Story 2 - Compaction Survival and Non-Rediscovery (Priority: P2)

A practitioner is deep in an investigation when the agent reaches 55% context fill and must apply `/compact` or start a fresh session. On reload, the agent reads the scratchpad as its context anchor before doing any new work. The practitioner then asks a follow-up question whose answer depends on earlier findings. The agent answers correctly from the scratchpad and does not re-run the exploratory steps that produced those findings.

**Why this priority**: This is the defining anti-pattern defense. The kata exists because agents that hold discoveries only inside the live conversation silently lose them after compaction, forcing wasteful rediscovery. A scratchpad that is written but never read back provides no value — this story proves the round trip.

**Independent Test**: Produce a scratchpad containing at least five tracked facts, force `/compact` or a new session, then issue a query that requires those facts. Verify zero rediscovery tool calls were made and the answer matches the recorded facts.

**Acceptance Scenarios**:

1. **Given** a scratchpad with recorded findings exists, **When** a new session starts, **Then** the agent reads the scratchpad before accepting its first user query.
2. **Given** a post-compaction session, **When** the practitioner asks about a topic covered by a previously recorded finding, **Then** the agent cites the scratchpad entry and performs no rediscovery exploration for that fact.
3. **Given** an agent that has just reloaded the scratchpad, **When** a new finding contradicts a recorded one, **Then** the agent surfaces the conflict rather than silently overwriting.

---

### User Story 3 - Machine-Parseable Structure on Inspection (Priority: P3)

A practitioner opens the scratchpad directly to audit what the agent has learned. The file is organized into declared, named sections (not a single prose blob), each finding carries enough metadata to be located and understood out of context, and the file can be mechanically parsed for downstream tooling.

**Why this priority**: The anti-pattern of "unstructured prose dumped into a scratchpad" makes the file unusable on reload and defeats the purpose of persistence. Structure is what makes the file useful as a context anchor for future sessions and for humans performing review.

**Independent Test**: Take a scratchpad produced by a real investigation and run a structural validator against its declared schema. 100% of findings must live under a recognized section and include the required fields.

**Acceptance Scenarios**:

1. **Given** a populated scratchpad, **When** a parser reads the file, **Then** every finding maps to exactly one declared section and exposes its required fields.
2. **Given** a practitioner opens the scratchpad, **When** they scan it visually, **Then** sections are clearly delimited and findings are individually identifiable rather than merged into prose.
3. **Given** a finding lacking required metadata, **When** it is written, **Then** the write is rejected or the missing metadata is flagged for follow-up.

---

### Edge Cases

- **Unbounded growth**: The scratchpad accumulates findings across many sessions and exceeds a reasonable size for context anchoring. The system must cap size or rotate before the file itself becomes too large to reload cheaply.
- **Conflicting findings**: A later finding contradicts an earlier one (e.g. "module X is the router" vs. "module Y is the router"). The system must detect the conflict, mark both entries, and not silently drop either.
- **Missing scratchpad at session start**: The declared scratchpad path does not exist (first run, deleted, wrong working directory). The agent must treat this as "no prior context" rather than failing, and create the scratchpad on the next write.
- **Concurrent edits**: Two sessions (or the agent and a human) write to the scratchpad simultaneously. The system must not produce a corrupted, half-written, or interleaved file.
- **Partial write during termination**: The process dies mid-write. The scratchpad must remain parseable — either the new finding is fully present or fully absent.
- **Finding too large for a single entry**: A discovery is larger than any reasonable section entry. The system must either summarize or reject, never silently truncate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The agent MUST persist every critical finding to a declared scratchpad file at the moment the finding is made, not batched to end-of-session.
- **FR-002**: The scratchpad MUST conform to a declared section structure; every written finding belongs to exactly one named section.
- **FR-003**: At session start, the agent MUST read the scratchpad if it exists and treat its contents as authoritative prior context before answering any new query.
- **FR-004**: The system MUST detect when a new finding conflicts with an existing recorded finding and flag both entries rather than silently overwriting.
- **FR-005**: The system MUST enforce a declared size cap on the scratchpad (`MAX_SCRATCHPAD_BYTES = 100_000` bytes) and trigger a rotation event when the cap is reached, preserving prior content in an archive rather than deleting it.
- **FR-006**: Each finding MUST carry the metadata required by the declared section schema (for example: identifier, timestamp, source query, section tag) so it is interpretable out of conversational context.
- **FR-007**: When the declared scratchpad path is missing at session start, the agent MUST proceed as a cold start and create the file on first write rather than erroring out.
- **FR-008**: Writes to the scratchpad MUST be atomic with respect to process termination; a crashed write must leave the file in a parseable state.
- **FR-009**: After a `/compact` or equivalent loop reset, the agent MUST re-read the scratchpad before accepting the next user query.
- **FR-010**: The scratchpad MUST be machine-parseable against its declared schema; unstructured prose dumps are a defect, not an acceptable form of capture.

### Key Entities

- **Investigation Session**: A bounded period of exploratory work by the agent. Has a start event, a stream of findings, and an end event (natural close, compaction, or termination). Each session is anchored to exactly one scratchpad file.
- **Scratchpad Section**: A declared, named region of the scratchpad (for example: routing map, open questions, confirmed invariants, conflicts). Sections exist before any findings are written and define where findings are allowed to land.
- **Finding**: A single durable discovery produced during an investigation. Has an identifier, a section assignment, the content of the discovery, and enough metadata to be understood without the originating conversation.
- **Rotation Event**: The archival action taken when the scratchpad reaches its declared size cap. Produces a preserved prior file and a fresh active scratchpad that retains any declared carry-over (for example: confirmed invariants).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Post-compaction rediscovery rate of tracked facts is 0 — across test runs, zero findings already present in the scratchpad are re-derived by the agent after a `/compact` or session reload.
- **SC-002**: 100% of findings captured in any test run conform to the declared section schema (correct section assignment and all required metadata fields present).
- **SC-003**: The scratchpad is successfully read by the agent at session start in 100% of test runs where the file exists, and a missing file results in a clean cold start in 100% of runs where it does not.
- **SC-004**: The declared size cap is never exceeded without a rotation event being emitted — across all test runs, no observation of an active scratchpad larger than the cap.
