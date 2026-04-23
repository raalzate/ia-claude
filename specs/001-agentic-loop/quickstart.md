# Kata 1 — Quickstart

## What you'll build

A minimal Python agent loop that decides what to do next by reading the
Messages API's `stop_reason` field — and nothing else. Every iteration writes
one JSONL line to an event log. From that log alone you can reconstruct the
loop's full trajectory.

## Prerequisites

- Python 3.11+
- `uv` or `pip` for dependency install
- An Anthropic API key in `ANTHROPIC_API_KEY` — **only** needed when running
  against the live API; the default test run uses recorded fixtures.

## Install

```bash
# From repo root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # pyproject.toml defines `anthropic`, `pydantic`, `pytest`, `pytest-bdd`
```

## Run the kata against recorded fixtures (default — no API key needed)

```bash
pytest tests/katas/001_agentic_loop -v
```

You should see:
- the Gherkin `agentic_loop.feature` scenarios pass,
- the AST lint `tests/katas/001_agentic_loop/lint/test_no_prose_matching.py` pass
  (proving the loop source doesn't import `re` or call `str.find`),
- the unit tests pass.

## Run the kata against the live API

```bash
LIVE_API=1 python -m katas.001_agentic_loop.runner \
  --model claude-opus-4-7 \
  --prompt "What's the weather in Bogotá? Use the get_weather tool."
```

Artifacts produced:
- `runs/<session-id>/events.jsonl` — the JSONL event log (one line per iteration)
- `runs/<session-id>/history.json` — the full conversation history (optional mirror)

## Verify deterministic behavior

Inspect the event log:

```bash
jq -c '{iter: .iteration, signal: .stop_signal, branch: .branch_taken, tool: .tool_name, cause: .termination_cause}' \
  runs/<session-id>/events.jsonl
```

Every iteration records its `stop_signal` and the branch taken. Exactly one
line has a non-null `termination_cause`. No text-derived field exists on any
record.

## Test scenarios (mapped to spec acceptance)

| Scenario | Spec ID | Fixture |
|----------|---------|---------|
| Happy path: tool_use → end_turn | US1-AS1, US1-AS2, US1-AS3 | `happy_path.json` |
| Decoy completion phrase ignored | US2-AS1, US2-AS2, US2-AS3, SC-004 | `decoy_phrase.json` |
| Max-tokens stop halts with labeled reason | Edge #1, FR-006, SC-006 | `max_tokens.json` |
| Malformed tool_use halts | Edge #3, FR-008 | `malformed_tool_use.json` |
| Unknown stop signal halts | Edge #4, FR-006, SC-006 | `unknown_signal.json` |
| Absent stop signal halts | Edge #5, FR-006, SC-006 | `absent_signal.json` |

## What "done" looks like (per Constitution §Kata Completion Standards)

- [ ] `spec.md`, `plan.md`, `tasks.md`, `.feature` file all exist — ✅ first three done, testify next.
- [ ] Acceptance scenarios cover objective AND anti-pattern — ✅ US1 + US2.
- [ ] Evaluation harness uses signal-level assertions only — ✅ per `test_event_log_shape.py`.
- [ ] Anti-pattern test fails closed if regex-on-prose is reintroduced — ✅ AST lint.
- [ ] Assertion-integrity hashes in `.specify/context.json` match locked test set — done at `/iikit-04-testify`.
- [ ] Per-kata `README.md` with objective / walkthrough / anti-pattern defense / run instructions / reflection — written during `/iikit-07-implement`.
- [ ] Every non-trivial function carries a *why* comment — enforced during implement review.

## Reflection prompt (answered at implement time)

- Which prose phrase was most tempting to match on, and what stopped you?
- Where in the code would `re` sneak back in during maintenance, and how does
  the AST lint catch it?
