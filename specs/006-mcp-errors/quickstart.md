# Kata 6 — Quickstart

## What you'll build

An MCP server that turns every failure into a typed payload (`isError=true` +
`StructuredError { errorCategory, isRetryable, detail }`) and an agent-side
retry loop that branches on that metadata — never on the text of the message.
Exhausted retries route to a typed `EscalationTrigger`.

## Prerequisites

- Python 3.11+
- `uv` or `pip`
- `ANTHROPIC_API_KEY` only for `LIVE_API=1` runs

## Install

```bash
pip install -e ".[dev]"
```

## Run against recorded fixtures (default)

```bash
pytest tests/katas/006_mcp_errors -v
```

Includes the AST lint at `tests/katas/006_mcp_errors/lint/test_no_generic_failures.py`
that fails the build if the server module emits a bare `"Operation failed"`
or equivalent unqualified message.

## Run against the kata's MCP server (live)

```bash
# Terminal 1
python -m katas.006_mcp_errors.server

# Terminal 2
LIVE_API=1 python -m katas.006_mcp_errors.runner --scenario transient-recover
```

Artifacts:
- `runs/<session-id>/events.jsonl` — per-call `call_id`, `errorCategory`, `isRetryable`, `attempt`, terminal outcome
- `runs/<session-id>/escalations/*.json` — emitted on budget exhaustion

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Transient error retries and succeeds | US1, FR-004, SC-003 | `transient_recover.json` |
| Validation error routes to escalation | US2, FR-005, Edge #2 | `validation_failure.json` |
| Retry budget exhausted → escalation | Edge #3 | `budget_exhausted.json` |
| Chained failures | Edge #4 | `chained_failures.json` |
| Non-conformant server payload rejected | Edge #2 | `malformed_response.json` |
| Network failure before MCP response | Edge #1 | `network_drop.json` |

## "Done" checklist (Constitution §Kata Completion Standards)

- [x] `spec.md`, `plan.md`, `tasks.md`, `.feature` — first two done; testify + tasks pending.
- [x] Acceptance scenarios cover objective AND anti-pattern (generic error).
- [ ] Signal-level assertions only — verified at `/iikit-04-testify`.
- [ ] Anti-pattern test fails closed if server emits a generic string — AST lint in place.
- [ ] Assertion-integrity hashes locked — done at `/iikit-04-testify`.
- [ ] `README.md` with objective / walkthrough / anti-pattern defense / run / reflection — at `/iikit-07-implement`.
- [ ] Every non-trivial function carries a *why* comment — enforced during implement review.

## Open items

- SC-003 threshold ("≥ X%" in spec) resolved in `research.md` D-00X as "≥ 95% of
  transient failures recover within declared budget on the fixture corpus".
  Revisit if fixture distribution changes.

## Reflection prompt (for `/iikit-07`)

- Where is the temptation to log a prose-only "Operation failed"? What prevented it?
- When would you raise `max_attempts` and why is that a risk?
