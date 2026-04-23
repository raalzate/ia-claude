# Phase 0 Research: PostToolUse Cognitive Load Normalization

## Decisions

### D-001 — Reuse the shared Kata baseline (Python 3.11+, pydantic v2, pytest+pytest-bdd)

- **Decision**: Adopt the same language / schema / test tooling the workshop
  already uses in Kata 1 (`specs/001-agentic-loop/plan.md`). No new baseline
  tech introduced for this kata.
- **Rationale**: Constitution v1.3.0 Development Workflow treats the 20 katas
  as a portfolio; sharing baseline decisions keeps cross-kata review meaningful
  and prevents accidental framework divergence. Pydantic v2 directly satisfies
  Principle II for FR-002.
- **Alternatives considered**:
  - *msgspec / attrs.* Rejected: no reuse benefit — would re-teach the schema
    boundary from scratch.
  - *dataclasses + jsonschema.* Rejected: forces hand-rolled validation that
    duplicates pydantic's work (same reason as Kata 1 D-002).

### D-002 — `PostToolUseHook` protocol + `LegacyDBNormalizer` implementation

- **Decision**: Define `PostToolUseHook` as a `typing.Protocol` with a single
  method: `normalize(raw: RawToolResponse) -> NormalizedPayload`. Ship one
  concrete implementation, `LegacyDBNormalizer`, in `hook.py`. Registration
  binds `LegacyDBNormalizer` to the legacy-source tool name so every
  `tool_result` for that tool flows through it before being appended to the
  model's history.
- **Rationale**: A typed protocol is the minimum surface that satisfies FR-001
  without prescribing a runtime framework. A second implementation (e.g. a
  `NoOpHook`) is trivially pluggable and is exactly how US2 runs the anti-
  pattern baseline — by substituting the hook, not by editing the loop.
- **Alternatives considered**:
  - *ABC with inheritance.* Rejected: heavier than Protocol; inheritance is
    not needed to satisfy structural typing.
  - *Function-only (no protocol).* Rejected: loses the type signature that
    keeps hooks composable and testable in isolation.

### D-003 — XML parser: `lxml` over stdlib `xml.etree.ElementTree`

- **Decision**: Use `lxml.etree.XMLParser(resolve_entities=False,
  no_network=True, recover=True)` inside a thin wrapper in `parser.py`. The
  wrapper is the only module in the kata that touches `lxml`; everything
  downstream operates on a plain `dict`.
- **Rationale**: The Principle "don't add dependencies without reason" is
  satisfied by three concrete requirements that the stdlib cannot meet:
  1. **FR-007 (malformed input)**: `lxml`'s `recover=True` keeps parsing past
     unclosed tags and truncated blocks, producing a partial tree we can flag
     `parse_degraded`. `xml.etree.ElementTree` raises `ParseError` at the first
     malformed byte — we would have to hand-roll recovery.
  2. **XXE / billion-laughs hardening**: `lxml`'s
     `resolve_entities=False, no_network=True` is a one-line defusing
     configuration. Stdlib `xml.etree.ElementTree` is not hardened by default;
     the Python docs themselves recommend `defusedxml` (which would then be
     the added dependency anyway).
  3. **Oversized payloads (Edge: very large)**: `lxml.etree.iterparse` gives
     us bounded-memory streaming without loading the full DOM. The stdlib
     equivalent exists but combined with (1) and (2) the stdlib path requires
     two extra dependencies (`defusedxml`) and bespoke recovery code — net
     more surface than `lxml` alone.
- **Alternatives considered**:
  - *stdlib `xml.etree.ElementTree` + `defusedxml`.* Rejected: still needs
    hand-rolled recovery for FR-007, and adds `defusedxml` — so we pay a
    dependency cost without solving the actual problem.
  - *Regex-over-XML.* Hard-rejected: this is the anti-pattern the kata is
    defending against; parsing structured legacy markup by pattern-matching
    would violate the spirit of Principle I even though the kata's main
    determinism story is schema boundaries.
  - *Pure string strip (`.replace('<tag>', '')`).* Rejected: fails on nested
    blocks (Edge #5) and cannot extract status codes deterministically.

### D-004 — Explicit `dict[str, str]` status mapping with `"unknown"` fallback

- **Decision**: `STATUS_MAPPING` is a module-level `dict[str, str]` constant
  in `normalizer.py`. Lookup is `STATUS_MAPPING.get(raw_code)`; a `None`
  return is translated **exactly** into
  `{"code": "unknown", "raw": raw_code}` in the normalized payload — never a
  guessed or model-completed label (FR-003, SC-003). Extending coverage is a
  one-line dict edit and a test addition (US3).
- **Rationale**: Principle II treats mapping lookup as a schema boundary. A
  dict is the narrowest, most auditable form of that boundary — a new mapping
  shows up in `git diff` as a single line. Surfacing unknowns as a structured
  marker preserves the audit trail at the model-facing layer without
  fabricating data.
- **Alternatives considered**:
  - *YAML / JSON config file.* Rejected for Kata 3: adds a runtime load step
    without changing behavior; the dict-in-module approach keeps diffs
    obvious. A config file could be added later if the mapping grows large,
    but that is YAGNI today.
  - *Enum with a `default_factory`.* Rejected: enums don't gracefully admit
    new members at runtime, and the default-factory pattern invites the
    "guess a label" anti-pattern that FR-003 forbids.

### D-005 — Audit log: append-only JSONL at `runs/<session-id>/audit.jsonl`

- **Decision**: Write one `AuditRecord` per intercepted tool response as a
  JSON object on its own line. The full raw payload bytes are embedded
  (base64-encoded when non-UTF8) so the log is self-contained. `fsync` is
  called on close.
- **Rationale**: FR-005 + SC-004 require **100%** retention, byte-for-byte.
  JSONL is trivially greppable, append-safe across crashes, and matches the
  pattern already used by Kata 1's event log — so reviewers don't context-
  switch between formats.
- **Alternatives considered**:
  - *SQLite.* Rejected: retrieval semantics ("give me the raw for tool_use_id
    X") don't need a query engine; `jq` over JSONL is enough.
  - *Separate files per response.* Rejected: breaks append-only semantics and
    complicates SHA-256 roundtrip tests.

### D-006 — Token-count measurement for SC-001

- **Decision**: Primary path uses the `anthropic` SDK's tokenizer when it is
  available in the installed version (called once per payload via a thin
  wrapper in `tokens.py`). Fallback path, used only when the SDK tokenizer is
  not exposed in the installed `anthropic` version, is a documented stub
  counter: `len(text.split())` applied identically to both baseline and
  normalized payloads, so the *ratio* remains comparable even if the
  *absolute* count is an approximation. The README records which counter was
  used for the recorded measurement.
- **Rationale**: SC-001 is a ratio assertion (≥70% reduction). A consistent
  counter on both sides is what matters; the approximation is disclosed in
  the written doc so a reader is never misled about the metric.
- **Alternatives considered**:
  - *tiktoken.* Rejected: OpenAI tokenizer, not Claude — off-brand and
    potentially misleading in a Claude-focused kata.
  - *Live `/v1/messages/count_tokens` round-trip.* Rejected for the default
    offline test path; allowed under `LIVE_API=1` for a one-off calibration.

### D-007 — Single-project layout; mirror Kata 1 directory conventions

- **Decision**: `katas/003_posttool_normalize/` + `tests/katas/003_posttool_normalize/`.
  No shared library with Kata 1.
- **Rationale**: Same reasoning as Kata 1 D-006 — FDD vertical delivery,
  independent grading, no premature coupling.
- **Alternatives considered**:
  - *Promote audit log / event log to a shared `katas/_common/` package.*
    Rejected until a third kata actually needs the same writer; otherwise
    it's speculative abstraction.

## Tessl Tiles

`tessl search posttooluse` and `tessl search xml-normalization` (run
2026-04-23) returned no tiles covering XML normalization hooks or the
Anthropic PostToolUse idiom. **No tiles installed for this feature.** If a
community tile later appears under keywords `anthropic-hooks`,
`posttooluse`, or `xml-sanitizer`, revisit at Kata 4 plan time. No eval
scores recorded.

## Unknowns Carried Forward

None. Every spec requirement traces to a decision above:

- FR-001 → D-002 (hook protocol interposes before history append)
- FR-002 → D-001 (pydantic v2) + contracts JSON Schemas
- FR-003 → D-004 (explicit dict + `unknown` marker)
- FR-004 → D-002 + FR-004 markup-leak test (`test_hook_markup_leak.py`)
- FR-005 → D-005 (append-only JSONL audit)
- FR-006 → D-002 (hook returns `NormalizedPayload`; runner appends that)
- FR-007 → D-003 (`lxml` recover=True + defused parser)
- SC-001 → D-006 (token counter + ratio assertion)
- SC-002 → FR-004 test
- SC-003 → D-004 unit test (`test_normalizer_unknown_code.py`)
- SC-004 → D-005 roundtrip test (`test_audit_roundtrip.py`)

No `NEEDS CLARIFICATION` remains.
