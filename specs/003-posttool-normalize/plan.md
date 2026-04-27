# Implementation Plan: PostToolUse Cognitive Load Normalization

**Branch**: `003-posttool-normalize` | **Date**: 2026-04-23 | **Spec**: [`spec.md`](./spec.md)
**Input**: Feature specification from `/specs/003-posttool-normalize/spec.md`

## Summary

Interpose a `PostToolUseHook` between legacy-source tool responses and the model's
conversation history. The hook (a) persists the raw XML + status-code payload to
an immutable audit log (FR-005, SC-004), (b) parses the XML with a narrow,
defusing parser, (c) maps arcane status codes through an explicit `dict[str, str]`
normalization table with an `"unknown"` fallback marker (FR-003, SC-003), and
(d) emits a minimal pydantic `NormalizedPayload` that is the only artifact the
model ever sees (FR-004, FR-006). Success is measured by a ≥70% token reduction
vs. the raw payload across a recorded fixture corpus (SC-001). Built under
Constitution v1.3.0 Principles II (NN — schema-enforced normalization boundary),
III (Context Economy — the entire reason the hook exists), and VIII (NN —
mandatory *why* comments + README).

## Technical Context

**Language/Version**: Python 3.11+ (shared baseline with Kata 1).
**Primary Dependencies**:
- `anthropic` — used for PostToolUse wiring semantics and for a token counter
  when available (see D-006 in `research.md`); no control-flow coupling here
  beyond the tool-result message injection point the kata intercepts.
- `pydantic` v2 — `NormalizedPayload`, `StatusMapping`, `AuditRecord`,
  `RawToolResponse` are all pydantic models (Principle II / FR-002).
- `lxml` — narrow XML parser used with `resolve_entities=False` and
  `no_network=True` to harden against XXE / billion-laughs while handling
  real-world malformed legacy markup (FR-007, Edge: malformed). Alternative
  (`xml.etree.ElementTree`) rejected in `research.md` D-003.
- `pytest` + `pytest-bdd` — BDD runner consuming `.feature` files from
  `/iikit-04-testify`.
**Storage**: Local filesystem only. Audit log written as append-only JSONL at
`runs/<session-id>/audit.jsonl` (FR-005). Normalization map is a single Python
module (`normalizer.py`) containing a `dict[str, str]` constant — extending
coverage is a data change only (FR-003, US3-AS2).
**Testing**: pytest + pytest-bdd for acceptance; plain pytest for unit tests.
Recorded JSON fixtures under `tests/katas/kata_003_posttool_normalize/fixtures/`
cover representative legacy payloads (happy, malformed, unknown code, empty,
oversized, nested). Live API is gated behind `LIVE_API=1` per shared baseline
and is **not** required to exercise the hook — the hook operates on tool
results, which are fixture-injectable.
**Target Platform**: Developer local (macOS/Linux) + GitHub Actions Linux.
**Project Type**: Single project — one kata package under
`katas/kata_003_posttool_normalize/` with mirrored tests.
**Performance Goals**: Normalize a fixture payload in <50 ms on dev hardware.
Not latency-bound; assertion is bounded memory on oversized input (Edge: very
large) — streaming iter-parse where needed.
**Constraints**:
- FR-004 is absolute: raw legacy markup characters MUST NOT appear in the
  message appended to conversation history, even under parse failure or empty
  input. Enforced by a test that scans the emitted `NormalizedPayload` for
  legacy-markup characters (`<`, `>`, CDATA sentinels) in any string field.
- FR-003 forbids guessing: unknown codes produce
  `{"code": "unknown", "raw": "<arcane-code>"}` — never a fabricated label.
  Enforced by a unit test that feeds a deliberately absent code and asserts
  the `unknown` marker shape.
- SC-001: token count of normalized ≤ 30% of raw (i.e. ≥70% reduction)
  averaged over the fixture corpus. Measured with the `anthropic` tokenizer
  when available; the documented fallback is a deterministic whitespace-split
  token count (`len(text.split())`) used identically on baseline and
  normalized payloads when the `anthropic` tokenizer is unavailable (see D-006).
- SC-004: 100% of raw payloads retrievable byte-for-byte from the audit log.
  Enforced by a test that SHA-256s every raw fixture, runs it through the
  hook, and reopens `audit.jsonl` to assert the stored raw matches.
**Scale/Scope**: One kata, ~350–500 LOC implementation + comparable test code;
one README; fixture corpus ≤ 10 recorded payloads spanning the stated edge
cases.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle | How the plan satisfies it |
|-----------|---------------------------|
| I. Determinism Over Probability (NN) | Normalization is a pure function of (raw bytes, StatusMapping). No probabilistic fallback exists: unknown codes surface as a structured `{"code": "unknown", "raw": ...}` marker — never a model-inferred label (FR-003, SC-003). |
| II. Schema-Enforced Boundaries (NN) | `NormalizedPayload`, `StatusMapping`, `AuditRecord`, and `RawToolResponse` are pydantic v2 models with JSON Schema counterparts in `contracts/`. Invalid normalized output raises; no best-effort parse reaches the model (FR-002, FR-004). |
| III. Context Economy | The hook's **only** reason to exist. SC-001 enforces ≥70% token reduction vs. raw payload; the normalized shape is flat / shallow and field-bounded so attention dilution is minimized. |
| IV. Subagent Isolation | Not applicable — single-agent kata. |
| V. Test-First Kata Delivery (NN) | `/iikit-04-testify` runs before production code; `tasks.md` will reference test spec IDs. Anti-pattern test (US2) asserts the baseline run leaks raw markup into history and fails closed if the hook is bypassed. |
| VI. Human-in-the-Loop | Not load-bearing (no destructive actions). Degraded parses are flagged with an explicit `parse_degraded` marker so a human reviewer can find them in the audit log. |
| VII. Provenance & Self-Audit | Audit log at `runs/<session-id>/audit.jsonl` retains every raw payload byte-for-byte (FR-005, SC-004). Each `AuditRecord` carries `tool_use_id`, UTC timestamp, and parse status for post-hoc review. |
| VIII. Mandatory Documentation (NN) | Every non-trivial function / hook / schema will carry a *why* comment tied to FR-XXX / SC-XXX / anti-pattern. A single `notebook.ipynb` produced at `/iikit-07-implement` is the Principle VIII deliverable: it explains the kata, results, every Claude architecture concept exercised, the architecture walkthrough, applied patterns + principles, practitioner recommendations, the contract details, run cells, and the reflection. No separate `README.md`. |

**Result:** PASS. Proceed.

## Project Structure

### Documentation (this feature)

```text
specs/003-posttool-normalize/
  plan.md              # this file
  research.md          # Phase 0 output (decisions, XML-parser choice, Tessl note)
  data-model.md        # Phase 1 output (entity schemas)
  quickstart.md        # Phase 1 output (how to run the kata)
  contracts/           # Phase 1 output (JSON Schemas, Draft 2020-12, $id kata-003)
    raw-tool-response.schema.json
    normalized-payload.schema.json
    status-mapping.schema.json
    audit-record.schema.json
  tasks.md             # (generated by /iikit-05-tasks)
  checklists/
    requirements.md    # (already present — Phase 1 output of /iikit-01)
  # (kata narrative lives in katas/.../notebook.ipynb — no spec-side README)
```

### Source Code (repository root)

```text
katas/
  kata_003_posttool_normalize/
    __init__.py
    hook.py               # PostToolUseHook protocol + LegacyDBNormalizer impl
    normalizer.py         # STATUS_MAPPING: dict[str, str] + normalize() pure fn
    parser.py             # lxml wrapper: defused, malformed-tolerant XML -> dict
    models.py             # pydantic: RawToolResponse, NormalizedPayload, StatusMapping, AuditRecord
    audit.py              # AuditLog writer (append-only JSONL, fsync on close)
    tokens.py             # token counter (anthropic tokenizer w/ documented stub fallback)
    runner.py             # CLI: baseline (hook off) vs. normalized (hook on) comparison
    notebook.ipynb        # Principle VIII deliverable — kata narrative + Claude architecture certification concepts (written during /iikit-07)

tests/
  katas/
    kata_003_posttool_normalize/
      conftest.py         # fixture loader, audit-log assertions, token-count harness
      features/           # Gherkin from /iikit-04-testify
        posttool_normalize.feature
      step_defs/
        test_posttool_normalize_steps.py
      unit/
        test_normalizer_unknown_code.py   # FR-003, SC-003
        test_hook_markup_leak.py          # FR-004, SC-002 (scans for '<','>','CDATA')
        test_audit_roundtrip.py           # FR-005, SC-004 (sha256 before/after)
        test_token_reduction.py           # SC-001 (≥70% average across corpus)
        test_mapping_extension.py         # US3: add one entry, observe resolved label
      fixtures/
        happy_path.json            # representative legacy XML + known codes
        malformed_markup.json      # unclosed tags / truncated block (Edge: malformed)
        unknown_code.json          # code not in STATUS_MAPPING (Edge: unknown)
        empty_response.json        # empty body (Edge: empty)
        oversized_payload.json     # well beyond typical (Edge: large)
        nested_blocks.json         # legacy inside legacy + multi-code (Edge: nested)
```

**Structure Decision**: Same single-project layout as Kata 1 — sibling package
under `katas/NNN_<slug>/` with mirrored tests. No cross-kata shared library
introduced; the pydantic + anthropic + pytest baseline is declared once in
`pyproject.toml`. This keeps katas independently buildable and preserves FDD's
vertical-slice delivery cadence.

## Architecture

```
┌────────────────────┐
│   Agent Runtime    │
└─────────┬──────────┘
          │
┌────────────────────┐       ┌────────────────────┐
│  PostToolUse Hook  │───────│   Status Mapping   │
└─────────┬──────────┘       └────────────────────┘
          │
          ├─────────────┬─────────────────────┐
          │             │                     │
┌────────────────┐ ┌────────────────┐ ┌────────────────┐
│ Legacy DB Stub │ │Normalized Payl…│ │   Audit Log    │
└────────────────┘ └────────────────┘ └────────────────┘
```

Node roles: `Agent Runtime` is the kata entry point; `PostToolUse Hook` owns the core control flow
for this kata's objective; `Status Mapping` is the primary collaborator/policy reference;
`Legacy DB Stub`, `Normalized Payload`, and `Audit Log` are the persisted / external boundaries the kata
touches. Classifications written to `.specify/context.json.planview.nodeClassifications`.


## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `lxml` added as a new dependency | Legacy XML payloads include malformed fragments (Edge: malformed) and potentially untrusted entities. `lxml`'s `XMLParser(resolve_entities=False, no_network=True, recover=True)` handles both; stdlib `xml.etree.ElementTree` does not recover from malformed input and lacks entity-resolution controls — using it would force us to hand-roll error recovery, violating FR-007. Full justification in `research.md` D-003. | stdlib `xml.etree.ElementTree` alone cannot meet FR-007 without substantial custom recovery code; that custom code would itself be an undocumented new dependency on handwritten XML-recovery logic. |

_No other violations._ Intentionally out of scope: retries, streaming model
responses, persistent DB, cross-session state — none are required by the spec
or the constitution.
