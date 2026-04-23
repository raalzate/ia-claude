# Phase 0 Research: MCP Integration with Structured Error Handling

## Decisions

### D-001 — Reuse the `anthropic` Python SDK for agent-side loop

- **Decision**: Continue using `anthropic.Anthropic().messages.create(...)`
  for the agent loop that consumes `StructuredError` payloads. Branching keys
  off `StructuredError.isRetryable` (a typed bool), not `stop_reason`.
- **Rationale**: Kata 1 already adopted the official SDK (see
  `specs/001-agentic-loop/research.md` §D-001). Keeping the same dependency
  means Kata 6 composes on top of Kata 1 at implementation time — no parallel
  stacks, no re-teaching. Satisfies Principle I (Determinism) at the agent
  layer.
- **Alternatives considered**:
  - *Roll a custom dispatcher.* Rejected — reinvents what Kata 1 established
    and adds surface area unrelated to the structured-error lesson.
  - *LangChain tool wrappers.* Rejected — hides the `tool_use` → tool-result
    cycle behind callbacks and defeats the point of Principle II.

### D-002 — Pydantic v2 models for every MCP boundary

- **Decision**: `ToolCall`, `MCPResponse`, `StructuredError`, `RetryBudget`,
  `RecoveryAction`, and `EscalationTrigger` are all pydantic v2 models. Every
  MCP response runs through `MCPResponse.model_validate`. Missing fields or
  wrong types raise at boundary — the synthesizer path (D-007) catches these
  and emits a conformant `StructuredError` with `errorCategory="schema_violation"`.
- **Rationale**: Constitution Principle II (NN) — schemas prevent silent
  hallucination and make failures bisectable. FR-001, FR-002, and FR-007 are
  only tractable if the boundary is enforced; string matching the payload is
  the exact anti-pattern the kata is defending against.
- **Alternatives considered**:
  - *TypedDict / plain dict.* Rejected — no runtime enforcement, silently
    accepts garbage; direct Principle II violation.
  - *dataclasses + hand-rolled validation.* Rejected — duplicates pydantic's
    work; drift between code paths is a known regression source.

### D-003 — Enumerated `errorCategory` with explicit escape value

- **Decision**: `errorCategory: Literal["transient", "validation", "auth",
  "quota", "internal", "transport", "schema_violation"]`. Each mapped to a
  policy row in `policy.py`. `transport` covers network-layer failures before
  a payload ever lands (edge case 1 in spec); `schema_violation` covers
  non-conformant responses (edge case 2). No open "other" bucket — every
  value is a real branch.
- **Rationale**: Principle II expects enumerations to include an explicit
  escape value paired with a details field; here `StructuredError.detail`
  provides the free-form companion while the category set is closed, so
  silently typoed categories fail validation instead of slipping through.
  Traces to FR-002, SC-001.
- **Alternatives considered**:
  - *Free-string category.* Rejected — defeats SC-001 auditability.
  - *Open `Literal[...] | str` union.* Rejected — permits the anti-pattern
    (unknown category treated as retryable by accident).

### D-004 — `RetryBudget` is declared data, not ambient counter

- **Decision**: `RetryBudget(max_attempts=3, backoff_seconds=float)` is
  attached to each `ToolCall` at construction. Policy decisions call
  `budget.attempt()` which returns a new budget with remaining attempts
  decremented, or raises `BudgetExhausted`. Zero global state.
- **Rationale**: FR-005 says *configurable* and *enforced*. A typed budget
  that flows with the call is the only way to guarantee exhaustion routes
  cleanly to escalation (Principle VI) and is replayable from the error log
  (Principle VII). The default `max_attempts=3` is a conservative starting
  point; clarify can tune SC-003 separately from the budget itself.
- **Alternatives considered**:
  - *Retry counter on a shared object.* Rejected — race-prone, hard to
    reason about in chained-failures fixture (edge case 4).
  - *Decorator-based retry (e.g. `tenacity`).* Rejected — hides the
    branch the kata is teaching; the point is that *the agent* sees the
    retry budget as typed data.

### D-005 — Five-fixture corpus covering every branch

- **Decision**: Ship five JSON fixtures under
  `tests/katas/006_mcp_errors/fixtures/`:
  1. `retryable_success_after_retry.json` — transient failure, second
     attempt succeeds (US1, SC-003 numerator).
  2. `retryable_exhausted_budget.json` — same class of failure keeps
     recurring, budget exhaustion routes to escalation (edge case 3,
     SC-003 denominator minus the successful cases).
  3. `non_retryable_validation.json` — validation error, zero retries, direct
     escalation (US2, SC-004).
  4. `server_crash.json` — server returns a non-`isError` crash signal
     mid-turn; synthesizer produces a `StructuredError` with category
     `transport` (edge case 1, FR-007).
  5. `chained_failures.json` — one turn triggers three tool calls with mixed
     retryability; verifies each is handled independently (edge case 4).
- **Rationale**: Directly mirrors Kata 1's recorded-fixture approach
  (research.md D-004) and gives every acceptance scenario an offline fixture.
  Five is the minimum to cover P1+P2+P3 and the four declared edge cases
  without duplication.
- **Alternatives considered**:
  - *Single fixture with all branches.* Rejected — scenario isolation dies.
  - *Generate fixtures at runtime from the server itself.* Deferred — makes
    test output non-deterministic; can be added later as a "stress" mode.

### D-006 — MCP library: `mcp` reference Python SDK (stub fallback)

- **Decision**: Use the official `modelcontextprotocol/python-sdk`
  (PyPI: `mcp`) with the in-memory transport for tests and stdio transport
  for the `runner.py` live-run path. The kata's `MCPServer` registers one
  tool, `brittle_op`, which deliberately returns `isError=true` with a
  structured payload driven by input flags (`?fail_mode=transient|validation|
  crash`). If the `mcp` package proves unavailable or too heavy for CI,
  fall back to the stub server retained under `server.py` that implements
  only the response shape — the kata's lesson is the *payload contract*,
  not the transport.
- **Rationale**:
  - Using the reference SDK demonstrates the kata works against real-world
    MCP clients, not a toy — relevant for Principle VI (escalations are
    human-reviewable only if the transport is one humans recognize).
  - The stub fallback exists because Kata 1 established that CI must run
    offline by default; we do not block the kata on `mcp` availability in
    the pinned Python matrix.
- **Alternatives considered**:
  - *Only the stub server.* Rejected as the default — a fake MCP server
    risks teaching a fake contract; students would not recognize it in a
    real deployment.
  - *Only the SDK server, no stub.* Rejected as the default — adds a
    mandatory network/stdio dependency to the test suite for a single kata
    surface area; the stub exists for CI resilience.

### D-007 — Local synthesizer for transport and schema-violation failures

- **Decision**: `synthesizer.synthesize(cause)` produces a conformant
  `StructuredError` for every case where the MCP server did not produce one
  itself — namely (a) transport-level disconnects (edge case 1), and
  (b) server payloads that fail `MCPResponse.model_validate` (edge case 2).
  Mapping:
  - Transport drop → `errorCategory="transport", isRetryable=True,
    detail=<connection diagnostic>`.
  - Schema violation → `errorCategory="schema_violation", isRetryable=False,
    detail=<pydantic error summary>`.
- **Rationale**: FR-007 demands a structured payload in both cases; the
  synthesizer is the single chokepoint that guarantees the agent never sees a
  bare exception string or an unparseable response. Traces directly to
  SC-002 (0 generic strings observable).
- **Alternatives considered**:
  - *Raise an exception and let the agent loop catch it.* Rejected —
    exception text is exactly the generic-string anti-pattern.
  - *Default all categories to `transient`.* Rejected — schema violations
    are not retryable; the kata's point is that the category drives the
    branch.

### D-008 — Anti-pattern lint enforced at source

- **Decision**: `tests/katas/006_mcp_errors/lint/test_no_generic_error_strings.py`
  parses `katas/006_mcp_errors/server.py` with `ast` and grep-scans all
  string literals. A literal match against `{"Operation failed", "Error",
  "Something went wrong", "oops", "failure"}` fails the test.
- **Rationale**: SC-002 measures "0 generic failure strings observable". A
  lint at source is the only durable defense — runtime-only checks miss the
  pathway where a developer hand-writes `return {"error": "Operation
  failed"}`. The test is the same shape Kata 1 used (D-005 there, AST lint
  for regex-on-prose), keeping the teaching pattern consistent across katas.
- **Alternatives considered**:
  - *Runtime-only check on the emitted payload.* Rejected — too late to
    teach the lesson and doesn't prevent the bad literal from landing in a
    code review.
  - *ruff custom rule.* Deferred — layered on top later if needed.

## Tessl Tiles

`tessl search "mcp model context protocol"` (run 2026-04-23) returned 14
results. Findings:

- **`tessl/npm-modelcontextprotocol--sdk` v1.20.0** — TypeScript SDK.
  Non-applicable (this kata is Python).
- **`tessl/golang-github-com-modelcontextprotocol--go-sdk` v1.1.2** — Go SDK.
  Non-applicable.
- **No Python MCP SDK tile exists in the Tessl registry as of 2026-04-23.**

**Action**: Do not install a tile for this feature. Revisit on each subsequent
kata plan; if `tessl/pypi-mcp` (or equivalent) appears, evaluate for
`/iikit-07-implement`. No eval scores recorded. This note is the provenance
trace required by Principle VII.

## Unknowns Carried Forward

- **SC-003 threshold** — *NEEDS CLARIFICATION*. The spec still carries the
  "X%" placeholder. `plan.md` §Open Questions documents the proposed clarify
  path (95% on the success-possible subset of the fixture corpus). Testify
  MUST emit the SC-003 scenario with a `@needs-clarify` tag so the gap is
  visible until `/iikit-clarify` resolves it.
- **MCP SDK availability on the Python matrix** — track during `/iikit-07`.
  If the `mcp` package cannot be installed in CI, switch to the stub-only
  path declared in D-006 and record the switch in the README reflection.
