# Phase 0 Research: Hierarchical Memory Orchestration in CLAUDE.md

## Decisions

### D-001 — Deliverable IS the config; resolver is the test harness

- **Decision**: The canonical artifacts shipped by this kata are
  `.claude/CLAUDE.md` and `standards/*.md`. `MemoryResolver` is a *validator
  library* — it exists so the governance files can be unit-tested, not to
  replace Claude's native memory loader.
- **Rationale**: Kata 8 is config-heavy. The learning objective is the
  *hierarchical `@path` pattern* (already demonstrated by this repo's own
  `CLAUDE.md` → `AGENTS.md` → `.tessl/RULES.md` chain). Building a runtime
  loader would invent a parallel mechanism the agent doesn't use and invite
  drift between the validator and native behavior.
- **Alternatives considered**:
  - *Ship only the markdown, no Python library.* Rejected: Constitution V
    (TDD, NON-NEGOTIABLE) requires executable acceptance — without a resolver
    there is nothing to assert against for determinism (SC-001), size budget
    (SC-003), or missing-target diagnostics (SC-004).
  - *Fork a runtime loader replacement.* Rejected: duplicates native behavior
    with inevitable drift; scope creep beyond spec.

### D-002 — Python 3.11+ with stdlib-only resolver core

- **Decision**: Resolver uses `pathlib`, `hashlib`, `collections` only.
  `pydantic` v2 is the single third-party dep inside the resolver module;
  `anthropic` appears only in the fresh-clone behavior test.
- **Rationale**: `@path` grammar is a one-line token (`^@<path>$` on an
  otherwise-empty line); regex-free line scan is sufficient. A graph library
  would be pulled in only for cycle detection, which is a 15-line DFS with a
  `visiting` set. Constitution III (Context Economy) and the repo's "don't
  add surrounding cleanup" preference both argue against unnecessary deps.
- **Alternatives considered**:
  - *`networkx` for graph traversal.* Rejected as YAGNI — cycle detection is
    trivial and the whole point of the kata is to keep governance lean.
  - *`tomllib` / `PyYAML` for front-matter.* Rejected: spec does not require
    front-matter; `@path` lines are the only structured syntax.

### D-003 — Pydantic v2 models with JSON Schema mirrors under `contracts/`

- **Decision**: `ResolvedMemory`, `MemoryEntry`, `PathReference`, and
  `ResolutionDiagnostic` are pydantic v2 models. JSON Schema mirrors under
  `specs/008-claude-md-memory/contracts/` carry `$id`
  `https://ia-claude.local/schemas/kata-008/<name>.schema.json`. A unit test
  asserts the pydantic model and the JSON Schema agree (generated vs checked
  in).
- **Rationale**: Constitution II (Schema-Enforced Boundaries, NON-NEGOTIABLE).
  The schema mirrors make the contract consumable by downstream katas / CI
  tools that don't import Python.
- **Alternatives considered**:
  - *Pydantic only, no JSON Schema.* Rejected: JSON Schema is the cross-
    language contract; future katas may consume it without Python.
  - *Hand-written `dataclass` + validation.* Rejected — reinvents pydantic.

### D-004 — Deterministic DFS of `@path`, declaration-order preserved

- **Decision**: `MemoryResolver.resolve()` walks `@path` declarations in the
  **textual order they appear** in each file. It uses DFS: when a file
  declares `@A` then `@B`, A (and A's transitive dependencies) is fully
  resolved before B. Each `MemoryEntry` records `declaration_order: int` —
  the DFS position — and the output `ResolvedMemory.entries` list is sorted
  by that index. Identical source trees therefore produce byte-identical
  JSON serializations.
- **Rationale**: FR-005 + SC-001 require cross-clone reproducibility. DFS in
  declaration order is the minimum mechanism that achieves it and matches
  how a human reading `CLAUDE.md` top-to-bottom would expand the references.
- **Alternatives considered**:
  - *BFS.* Rejected: makes the order of a rule non-obvious from reading the
    source file.
  - *Alphabetical sort of referenced paths.* Rejected: breaks the author's
    intent when ordering matters (critical rules at the top / bottom of the
    window — Principle III).

### D-005 — Fail-loud via typed exceptions carrying `ResolutionDiagnostic`

- **Decision**: `MissingReferenceError`, `CircularReferenceError`,
  `UnreadableReferenceError`, and `OversizeMemoryError` all inherit from
  `MemoryResolutionError` and carry a `diagnostic: ResolutionDiagnostic`
  attribute. The resolver never silently skips a reference.
- **Rationale**: FR-004 and SC-004 make silent degradation a defect.
  Principle VI (Human-in-the-Loop) — a reviewer reading the raised
  diagnostic is the escalation target.
- **Alternatives considered**:
  - *Return a partial `ResolvedMemory` + warnings list.* Rejected — invites
    "just ignore the warnings" drift and contradicts SC-004's 100% rate.
  - *Log and continue.* Same objection, worse — the log is off-by-default in
    CI.

### D-006 — `TEAM_MEMORY_MAX_BYTES = 20 KB` declared in `budget.py`

- **Decision**: Constant `TEAM_MEMORY_MAX_BYTES = 20 * 1024` lives in
  `katas/008_claude_md_memory/budget.py`. `MemoryResolver.resolve()` computes
  aggregated team-scope size (sum of each `MemoryEntry.source_bytes` where
  `scope == "team"`). Exceeding the budget raises `OversizeMemoryError`.
  Lint test asserts the canonical template bundled in `templates/` stays
  under the budget.
- **Rationale**: Constitution III (Context Economy) — keep hard rules at the
  extreme edges of the window and don't bloat the stable prefix. 20 KB is a
  conservative working figure (roughly 5 k tokens); tuneable in a later
  amendment. Declaring it as a *named constant* makes the budget bisectable
  and amendable without touching code paths.
- **Alternatives considered**:
  - *Hard-code 20 KB inline.* Rejected: non-amendable without touching logic.
  - *Token-based budget via a tokenizer.* Rejected as overkill for a
    governance kata; byte size is a stable proxy.

### D-007 — Behavior-equivalence test uses `anthropic` SDK, one prompt, two clones

- **Decision**: One opt-in test (`LIVE_API=1 pytest -m live_api`) performs
  the SC-001 end-to-end check: set up two temp working copies of the kata
  `templates/` tree, resolve memory in each, send one scripted prompt to a
  Claude model with the resolved team memory injected as system prompt, and
  assert (a) byte-identical `ResolvedMemory` JSON and (b) the two agent
  responses land in the same categorical bucket on a structured tool call
  (not prose similarity). Default CI run uses the resolver-level determinism
  test only.
- **Rationale**: SC-001 as written is a behavioral claim ("identical agent
  behavior across developers"). Resolver-level byte equality is the
  deterministic half; the live test validates the claim still holds when
  the model receives the memory. Gating it behind `LIVE_API=1` keeps CI
  free of API quota while leaving the end-to-end check runnable.
- **Alternatives considered**:
  - *Live test as default CI.* Rejected — API cost + flake risk during
    workshop delivery.
  - *Skip live test entirely.* Rejected — spec SC-001 is a behavioral, not
    structural, claim; the live probe is the honest version.

## Tessl Tiles

`tessl search "claude md memory"` (run 2026-04-23): zero direct hits. Closest
adjacent topics were documentation-standards tiles, which are tangential.
`tessl search "hierarchical config"` / `"path reference resolver"` also
returned no relevant installable tiles. **No tiles installed for this
feature.**

Follow-up: if a tile codifying CLAUDE.md / AGENTS.md conventions later
appears (search terms: `claude-md`, `agents-md`, `hierarchical-memory`),
revisit this plan at kata 9 time. No eval scores recorded.

## Unknowns Carried Forward

None. The spec had no NEEDS CLARIFICATION markers; each edge case in §Edge
Cases maps to an FR covered by D-004..D-007 above.
