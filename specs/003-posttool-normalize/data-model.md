# Phase 1 Data Model: PostToolUse Cognitive Load Normalization

All entities below are implemented as pydantic v2 models at
`katas/003_posttool_normalize/models.py`. Validation runs on construction;
any invalid payload raises `pydantic.ValidationError` and the hook halts
with a parse-degraded marker instead of propagating the invalid shape.

## RawToolResponse

The opaque payload the legacy data source returns. Never reaches the model
directly (FR-004). Retained verbatim in the audit record (FR-005).

| Field | Type | Notes |
|-------|------|-------|
| `tool_use_id` | `str` | Echo of the SDK `tool_use_id` for correlation. |
| `tool_name` | `str` | Name of the legacy tool that produced this payload. |
| `raw_bytes` | `bytes` | The exact bytes the source returned — base64-encoded when serialized to JSONL so SHA-256 roundtrip (SC-004) is lossless. |
| `content_type` | `Literal["application/xml", "text/xml", "application/octet-stream"]` | Declared MIME; non-XML bodies still flow through but will surface as `parse_degraded`. |
| `received_at` | `datetime` (UTC) | When the hook observed the payload. |

**Invariants**
- `raw_bytes` is immutable after construction.
- `tool_use_id` uniquely identifies this response within a session (one
  `AuditRecord` per `tool_use_id`).

## StatusMapping

The declared `dict[str, str]` used to translate arcane status codes into
human-readable labels. Implemented as a pydantic wrapper around a frozen
mapping so it is validated at load time and diffable in source.

| Field | Type | Notes |
|-------|------|-------|
| `entries` | `dict[str, str]` | `raw_code → human_label`. Keys match the legacy source's encoding exactly (case-sensitive). Extending coverage adds one entry (US3). |
| `unknown_marker` | `Literal["unknown"]` | Constant. Used as the `code` value when a lookup misses. |

**Invariants**
- No empty keys, no empty values; duplicates are impossible in a dict.
- The string `"unknown"` MUST NOT appear as a value — reserved for the
  fallback marker so the miss path is unambiguous (FR-003, SC-003).
- Adding an entry is a pure data change: no other module in the kata is
  imported by `normalizer.py` that would need editing (US3-AS2).

## NormalizedPayload

The minimal, flat, field-bounded object the model actually sees. This is
the **only** form of a tool response that reaches conversation history
(FR-004, FR-006).

| Field | Type | Notes |
|-------|------|-------|
| `tool_use_id` | `str` | Same id as the originating `RawToolResponse` — keeps the audit ↔ context link inspectable. |
| `status` | `StatusField` | See below. One object, not a list — flat shape by design (Principle III). |
| `content` | `dict[str, Any]` | Cleaned, legacy-markup-free content extracted from the raw payload. Values are strings, numbers, bools, or shallow lists of those — no nested markup. |
| `parse_status` | `Literal["ok", "degraded", "empty"]` | `ok` on clean parse; `degraded` on malformed input (Edge: malformed); `empty` on no-body responses (Edge: empty). |
| `notes` | `list[str]` | Short, bounded list of machine diagnostics (e.g. `"unclosed_tag_recovered"`). Never contains model-facing prose or speculation. |

### StatusField

| Field | Type | Notes |
|-------|------|-------|
| `code` | `str` | Either the resolved human label from `StatusMapping.entries`, or the literal `"unknown"`. |
| `raw` | `str \| None` | Populated iff `code == "unknown"` — carries the original arcane code so the audit path stays explicit in context too (FR-003). Null when the code was resolved. |

**Invariants**
- No string field in `NormalizedPayload` or any nested value may contain
  `<`, `>`, or the CDATA sentinels — enforced by `test_hook_markup_leak.py`
  and by a pydantic `field_validator` on string-typed fields.
- `code == "unknown"` ⇒ `raw` is non-null and non-empty.
- `code != "unknown"` ⇒ `raw` is `None` (reserve the field for the miss path).
- Total payload size is bounded — deeply nested legacy input is flattened
  before construction (Edge: nested).

## AuditRecord

One line of `runs/<session-id>/audit.jsonl`. Source of truth for SC-004.

| Field | Type | Notes |
|-------|------|-------|
| `session_id` | `str` (UUID4) | Session this record belongs to. |
| `tool_use_id` | `str` | 1:1 with a `RawToolResponse`. |
| `tool_name` | `str` | Legacy tool name. |
| `received_at` | `datetime` (UTC) | When the raw payload was observed. |
| `raw_bytes_b64` | `str` | Base64 of `RawToolResponse.raw_bytes`. Byte-for-byte recoverable. |
| `raw_sha256` | `str` | Hex digest for cheap integrity checks during test roundtrip. |
| `parse_status` | `Literal["ok", "degraded", "empty"]` | Mirrors the eventual `NormalizedPayload.parse_status`. |
| `normalized_token_count` | `int` | Populated after normalization — feeds SC-001 reporting without requiring a second pass. |
| `raw_token_count` | `int` | Same, for the raw side of the ratio. |

**Invariants**
- Exactly one `AuditRecord` per intercepted response.
- The audit line is written **before** the hook appends the normalized
  message to history — so a crash mid-normalize cannot lose the raw
  payload (FR-005).
- `raw_sha256 == sha256(base64.b64decode(raw_bytes_b64))`; verified by
  `test_audit_roundtrip.py`.

## Relationships

```
Session
  ├── tool invocations (1..N)
  │     └── RawToolResponse              (never reaches model)
  │           ├── AuditRecord            (audit.jsonl, 1:1)
  │           └── NormalizedPayload      (appended to conversation history, 1:1)
  └── StatusMapping                      (module-level constant, shared across session)
```

## What is deliberately NOT modeled

- Multi-tool cross-correlation (Kata 3 is scoped to one legacy source).
- Retry / backoff on parse failure — `parse_degraded` is the terminal state;
  the human reviews the audit log.
- Rich nested content objects in `NormalizedPayload.content` — flatness is
  the whole point (Principle III). If a legacy payload genuinely has
  nested semantics, they are encoded as dotted keys in the flat dict, not
  as nested objects.
- Historical diff between old and new status mappings — out of scope; `git`
  handles it.
