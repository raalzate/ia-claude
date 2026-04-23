# Implementation Plan: Transactional Memory Preservation via Scratchpad

**Branch**: `018-scratchpad-persistence` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/018-scratchpad-persistence/spec.md`

## Summary

Build a Python kata module that defends against the context-cliff failure mode
by externalising every critical finding from an exploratory agent into a
durable, machine-parseable scratchpad file at the moment of discovery. A
`Scratchpad` pydantic model owns the structured source of truth: a fixed list
of named sections (`map`, `findings`, `open_questions`, `decisions`,
`conflicts`), each holding an ordered list of typed `Finding` entries
(`id`, `timestamp`, `category`, `evidence`, `source_ref`). The on-disk
representation is a markdown document with YAML frontmatter at
`investigation-scratchpad.md`; markdown rendering is a side output, never the
authority. A `ScratchpadWriter` exposes an append-only API
(`add_finding`, `note_conflict`, `resolve_open_question`) and serialises writes
through a POSIX `flock` so two sessions cannot interleave. At 55% context-window
fill — the same proactive-compaction threshold as kata 011 — a `ContextAnchor`
is assembled from the scratchpad's `decisions` + `open_questions` sections and
seeded into the next session; after resume the probe question "what did you
discover about module X?" is answered from the anchor with zero rediscovery
tool calls (SC-001). A structure validator parses the markdown back into a
`Scratchpad` and raises `ScratchpadSchemaError` on any drift (FR-002, FR-010,
SC-002). A declared `MAX_SCRATCHPAD_BYTES` cap triggers rotation to
`<name>.<iso-date>.md` with a carry-over "prior-pad" anchor, so the active
file never exceeds the cap (FR-005, SC-004). Delivered under Constitution
v1.3.0 principles III (Context Economy — load-bearing) and VIII (Mandatory
Documentation, NN), with II (Schema-Enforced Boundaries), V (TDD), VI (HITL
on conflict), VII (Self-Audit).

Tech choices trace to requirements:

- Python 3.11 + `pydantic` v2 (schemas per-entity) → FR-002, FR-004, FR-006,
  FR-010, SC-002, Principle II.
- `anthropic` SDK behind an injectable client → US2 compact-resume probe
  (SC-001), US1-AS3 termination survival.
- `pytest` + `pytest-bdd` for BDD acceptance, plain pytest for unit →
  Principle V, every FR/SC.
- `fasteners` (POSIX `flock` wrapper, stdlib-friendly) → FR-008 atomic writes,
  concurrent-edits edge case.
- `ruamel.yaml` for YAML frontmatter round-trip (preserves ordering) →
  FR-010 machine-parseable, FR-002 section schema.
- Offline fixtures + `LIVE_API=1` gate for the compact-resume probe → SC-001
  without burning CI quota.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**:
- `anthropic` (official Claude SDK) — sole transport for the compact-resume
  probe run behind `LIVE_API=1`; the SC-001 rediscovery-rate measurement needs
  a real model that did not see the original investigation turn.
- `pydantic` v2 — schema enforcement for `Scratchpad`, `Section`, `Finding`,
  `RotationEvent`, `ContextAnchor`, `ScratchpadSchemaError` payload (Principle
  II).
- `ruamel.yaml` — round-trip YAML frontmatter so the parser → model → emit
  cycle is lossless (FR-010).
- `fasteners` — POSIX-backed file lock wrapping `fcntl.flock`; serialises the
  append-only `ScratchpadWriter` across sessions (FR-008, concurrent-edits edge
  case). Chosen over stdlib `fcntl` directly so the same code runs on both
  developer macOS and Linux CI without platform branches.
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files produced by
  `/iikit-04-testify` (Principle V / TDD).

**Storage**: Local filesystem only. Per-run artifacts under
`runs/kata-018/<session-id>/`:
- `investigation-scratchpad.md` — active scratchpad (YAML frontmatter +
  markdown body). Source of truth is the parsed `Scratchpad` model; the file
  is the persistence format.
- `investigation-scratchpad.<iso-date>.md` — rotated archives (FR-005). Active
  file always begins with a fresh body plus a "prior-pad" anchor block.
- `rotation.jsonl` — append-only `RotationEvent` records (Principle VII).
- `anchor.json` — last-emitted `ContextAnchor` seeded into the compact-resume
  session (SC-001 auditing).

**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit. Default
test run is offline against fixture scratchpads under
`tests/katas/018_scratchpad_persistence/fixtures/`. The compact-resume probe is
gated by `LIVE_API=1` and runs only on explicit opt-in; the offline path
substitutes a `RecordedClient` returning a deterministic answer built from the
seeded anchor.

**Target Platform**: Developer local machine (macOS/Linux) and GitHub Actions
CI (Linux). Live probe runs locally or in a separately-scheduled CI job with
`ANTHROPIC_API_KEY`.

**Project Type**: Single project — one kata module under
`katas/018_scratchpad_persistence/` with tests alongside, matching the layout
established by kata 001.

**Performance Goals**: Not latency-bound. Offline acceptance completes under 5
seconds; scratchpad parse+validate of a rotation-sized file (<= 128 KiB by
default) completes under 50 ms. No p95 target on API latency — the kata's
goal is rediscovery=0 and schema=100%, not speed.

**Constraints**:
- Every write MUST go through `ScratchpadWriter`; direct file rewrites outside
  the writer are a test-level lint violation (FR-001, FR-008).
- `ScratchpadWriter` MUST hold a `flock` for the duration of a write, so
  concurrent sessions serialise rather than interleave (concurrent-edits edge
  case, FR-008).
- Conflict detection MUST emit both entries under the `conflicts` section with
  cross-references to the two `Finding.id`s — never silently overwrite
  (FR-004, US2-AS3, Principle VI).
- The structure validator MUST reject any section name outside the declared
  fixed list and any finding missing a required field; parse failures raise
  `ScratchpadSchemaError` with the byte offset of the failure (FR-002, FR-010,
  SC-002).
- `MAX_SCRATCHPAD_BYTES` is declared as a module constant; enforcement is
  post-write (stat the file; if over cap, rotate before returning) so a crash
  mid-write cannot leave an oversized active file (FR-005, SC-004).
- No regex-over-prose is used to decide "is this a conflict" or "is this a
  finding". Classification is driven by the typed `Finding.category` field,
  not by scanning the markdown body — matches the Principle I pattern carried
  forward from kata 001 / 011.

**Scale/Scope**: One kata, ~500–700 LOC implementation + comparable test code;
one `README.md` (Principle VIII); fixture corpus covering the five declared
edge cases (unbounded growth, conflicting findings, missing scratchpad,
concurrent edits, partial write) plus one happy-path mid-investigation
compact-resume.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Compaction bridge fires on numeric context-fill fraction (≥ 0.55), not on model prose. Conflict detection keys off typed `Finding.category` + declared equivalence, never on text search over findings. Structure validator consumes the parsed pydantic tree, never regex against the raw markdown body. |
| II. Schema-Enforced Boundaries (NN) | Every entity — `Scratchpad`, `Section`, `Finding`, `RotationEvent`, `ContextAnchor`, `ScratchpadSchemaError` — is a pydantic v2 model with JSON Schema exports under `contracts/` (`$id` prefix `https://ia-claude.local/schemas/kata-018/...`). Invalid payloads raise `ValidationError` and abort the write; the file is left untouched. |
| III. Context Economy (load-bearing) | This kata *is* the Principle III persistence kata. The scratchpad is the externalised memory that makes ≥ 50% context compaction survivable (spec §Principle III clause); the 55% threshold and the decisions+open-questions anchor operationalise the principle as executable code and BDD assertions. Aligns with kata 011's 55% compaction trigger so the two katas compose without contradiction. |
| IV. Subagent Isolation | Not load-bearing — single-agent kata. The `ContextAnchor` payload is typed and minimal, which is the same hub-and-spoke discipline the principle demands and is tested for shape conformance. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` will lock `.feature` files and assertion-integrity hashes before any production code. `tasks.md` (generated later by `/iikit-05-tasks`) references test IDs. This plan does NOT commit code. |
| VI. Human-in-the-Loop Escalation | Conflicting findings are routed to the `conflicts` section with both entries preserved and surfaced — the human reader is the escalation target; the agent never picks arbitrarily (US2-AS3, FR-004). Corrupted scratchpads fail loud with `ScratchpadSchemaError` rather than partial recovery. |
| VII. Provenance & Self-Audit | Each `Finding` carries `source_ref` (tool call id or session turn pointer); every rotation emits a `RotationEvent` into `rotation.jsonl`; every compact-resume emits an `anchor.json`. The three files together are sufficient to re-derive SC-001..SC-004 without re-running the live investigation. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function / validator will carry a *why* comment tied to the FR or the anti-pattern it defends against. Kata `README.md` (produced during `/iikit-07-implement`) will cover objective, walkthrough, anti-pattern defense, run instructions, and reflection. Quickstart already enumerates the §Kata Completion Standards checklist. |

**Result:** PASS. Proceed to Phase 0 / 1 artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/018-scratchpad-persistence/
  plan.md              # this file
  research.md          # Phase 0 — decisions D-001..D-008 + Tessl discovery
  data-model.md        # Phase 1 — Scratchpad, Section, Finding, RotationEvent, ContextAnchor
  quickstart.md        # Phase 1 — install, fixture run, compact-resume demo, scenario→spec map, §Kata Completion checklist
  contracts/           # Phase 1 — JSON Schemas (one per entity, $id kata-018)
    scratchpad-document.schema.json
    finding.schema.json
    rotation-event.schema.json
    context-anchor.schema.json
  checklists/
    requirements.md    # (already present — produced by /iikit-01)
  tasks.md             # (generated later by /iikit-05-tasks)
  README.md            # Principle VIII deliverable — written during /iikit-07
```

### Source Code (repository root)

```text
katas/
  018_scratchpad_persistence/
    __init__.py
    models.py                # pydantic v2: Scratchpad, Section, Finding, RotationEvent, ContextAnchor, ScratchpadSchemaError
    scratchpad.py            # Scratchpad model helpers: render_markdown(), from_markdown()
    writer.py                # ScratchpadWriter: add_finding, note_conflict, resolve_open_question (append-only, flock-serialised)
    validator.py             # Structure validator: markdown → Scratchpad, raises ScratchpadSchemaError on drift
    compaction_bridge.py     # 55% trigger → ContextAnchor builder → next-session seed
    rotation.py              # MAX_SCRATCHPAD_BYTES cap + rotation to <name>.<iso-date>.md with prior-pad anchor
    client.py                # Thin injectable Anthropic client wrapper (shared shape with katas 001/011)
    runner.py                # CLI entrypoint: `python -m katas.018_scratchpad_persistence.runner`
    README.md                # kata narrative — written during /iikit-07

tests/
  katas/
    018_scratchpad_persistence/
      conftest.py            # fixture loader, tmp scratchpad factory, RecordedClient, flock helper
      features/              # Gherkin files produced by /iikit-04-testify
        scratchpad_persistence.feature
      step_defs/
        test_scratchpad_persistence_steps.py
      unit/
        test_writer_append_only.py           # FR-001, US1-AS2
        test_writer_flock_serialises.py      # concurrent-edits edge case, FR-008
        test_validator_round_trip.py         # FR-002, FR-010, SC-002
        test_validator_rejects_drift.py      # FR-002 negative
        test_conflict_routing.py             # FR-004, US2-AS3
        test_compaction_bridge_threshold.py  # 55% trigger, matches kata 011
        test_context_anchor_shape.py         # SC-001 auditing
        test_rotation_cap.py                 # FR-005, SC-004
        test_missing_scratchpad_cold_start.py# FR-007
      lint/
        test_no_prose_classification.py      # AST check: writer/validator MUST NOT classify findings by text search
      fixtures/
        empty_scratchpad_reload.md
        mid_investigation_compact_resume.md
        corrupted_pad.md                     # must fail loud
        oversize_pad.md                      # triggers rotation
        conflicting_findings.md              # two findings with opposed evidence on same target
```

**Structure Decision**: Single-project layout, mirroring katas 001 and 011.
Kata 018 owns its `ScratchpadWriter`, `validator`, `compaction_bridge`, and
`rotation` modules in-tree; no shared cross-kata library is extracted yet.
A future refactor may hoist the 55% compaction threshold into a shared
`ContextEconomy` helper after kata 011 lands, but introducing it now would
couple two in-flight katas and violate the FDD "vertical delivery per kata"
rule in Constitution §Development Workflow. Live runs write to
`runs/kata-018/<session-id>/` (gitignored).

## Architecture

```
┌────────────────────┐
│ Investigator Agent │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│ Scratchpad Writer  │───────│  Scratchpad File   │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│Rotation Manager│ │ Context Anchor │ │Scratchpad Mess…│
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Investigator Agent` is the kata entry point; `Scratchpad Writer` owns the core control flow
for this kata's objective; `Scratchpad File` is the primary collaborator/policy reference;
`Rotation Manager`, `Context Anchor`, and `Scratchpad Messages API` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

_No violations._ Intentionally deferred: a cross-kata `ContextEconomy` helper
shared with kata 011 (revisit after both katas land), an SQLite-backed
scratchpad (a single markdown file + frontmatter is sufficient at workshop
scale and keeps the file human-auditable per Principle VIII), and an async
rotation worker (rotation is O(file-copy) and fires rarely; synchronous
rotation inside the writer is simpler and still inside the 50 ms parse
budget).
