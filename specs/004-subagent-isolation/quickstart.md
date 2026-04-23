# Kata 4 — Quickstart: Strict Subagent Context Isolation (Hub-and-Spoke)

## What you'll build

A `Coordinator` that decomposes a task into subtasks, spawns a `Subagent` per
subtask through a `TaskSpawner` dependency, and recomposes typed
`SubagentResult`s into a final answer. Each subagent runs in its own
`anthropic.Anthropic().messages.create` session seeded **only** from a
`SubtaskPayload` pydantic model. The coordinator's private history cannot
cross the boundary — enforced by an AST lint, a leak-probe integration test,
and `extra="forbid"` on every handoff schema.

## Prerequisites

- Python 3.11+
- `uv` or `pip` for dependency install
- An Anthropic API key in `ANTHROPIC_API_KEY` — **only** needed when running
  against the live API; the default test run uses recorded fixtures.

## Install

```bash
# From repo root
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"   # pyproject.toml defines anthropic, pydantic, pytest, pytest-bdd
```

## Run the kata against recorded fixtures (default — no API key needed)

```bash
pytest tests/katas/004_subagent_isolation -v
```

You should see:
- the Gherkin `subagent_isolation.feature` scenarios pass,
- the AST lint `tests/katas/004_subagent_isolation/lint/test_no_history_leak.py`
  pass (proving `subagent.py` has no reference to `Coordinator._history`
  or equivalent),
- the leak-probe integration test
  `tests/katas/004_subagent_isolation/integration/test_leak_probe.py` pass
  (UUID seeded in coordinator history is absent from every subagent input),
- the swap-equivalence unit test pass (stub subagent honoring the same
  `HandoffContract` leaves the coordinator unchanged),
- the malformed-result unit test pass (bad JSON → terminal
  `SubagentResultValidationError`, no silent fallback).

## Run the kata against the live API

```bash
LIVE_API=1 python -m katas.004_subagent_isolation.runner \
  --model claude-opus-4-7 \
  --prompt "Plan a 3-city weekend trip and summarize the weather at each stop."
```

Artifacts produced under `runs/<session-id>/` (gitignored):
- `coordinator_history.json` — the coordinator's own transcript (reference
  material for the auditor; never fed to subagents).
- `subagent_inputs.jsonl` — one line per spawned subagent, the exact
  serialized `SubtaskPayload`. This is the file the leak-probe check scans.
- `subagent_outputs.jsonl` — one line per return: the raw SDK response
  string AND the validated `SubagentResult.model_dump_json()` for diffable
  before/after.

## Verify isolation holds (manual audit)

```bash
# 1. Diff declared payload schema against every actual subagent input.
jq -c . runs/<session-id>/subagent_inputs.jsonl \
  | xargs -I{} ajv validate -s specs/004-subagent-isolation/contracts/subtask-payload.schema.json -d '{}'

# 2. Scan for coordinator history leaks (SC-001 / SC-004).
PROBE=$(jq -r '._probe_uuid' runs/<session-id>/coordinator_history.json)
grep -c "$PROBE" runs/<session-id>/subagent_inputs.jsonl   # expect: 0

# 3. Confirm every subagent output validated clean (SC-002).
jq -c '.validated' runs/<session-id>/subagent_outputs.jsonl \
  | xargs -I{} ajv validate -s specs/004-subagent-isolation/contracts/subagent-result.schema.json -d '{}'
```

## Test scenarios (mapped to spec acceptance)

| Scenario | Spec ID | Fixture |
|----------|---------|---------|
| Coordinator spawns per-subtask scoped payloads; each subagent receives only declared fields | US1-AS1, FR-001, FR-006 | `happy_path.json` |
| Subagent return is JSON-valid under `SubagentResult` schema; coordinator only consumes declared fields | US1-AS2, FR-003, SC-002 | `happy_path.json` |
| Leak-probe UUID seeded in coordinator history is absent from every subagent input | US2-AS1, FR-002, SC-001, SC-004 | `leak_probe.json` |
| Coordinator attempt to forward raw transcript as `inputs` is rejected by schema | US2-AS2, FR-001 | `leak_probe.json` (negative branch) |
| Swap one subagent implementation (same `HandoffContract`) — coordinator unchanged | US3-AS1, FR-008, SC-003 | `swap_equivalent.json` |
| Swapped subagent returns contract-violating output — coordinator surfaces terminal error | US3-AS2, FR-003, FR-004, SC-002 | `malformed_result.json` |
| Malformed JSON from subagent is terminal, no silent fallback | Edge Case #1, FR-004 | `malformed_result.json` |
| Extra/unexpected fields rejected per schema policy | Edge Case #2, FR-001, FR-003 | happy-path variant |
| Nested subagent spawning receives its own scoped payload only (no parent inheritance) | Edge Case #4, FR-007 | `nested_spawn.json` |

## §Kata Completion Standards checklist (Constitution v1.3.0)

- [ ] `spec.md`, `plan.md`, `tasks.md`, and `.feature` file all exist for Kata 4
      (plan done here; tasks + feature come after `/iikit-04-testify`).
- [ ] Acceptance scenarios cover both the stated objective (hub-and-spoke
      scoped fan-out, US1) AND the stated anti-pattern (shared-memory
      telepathy, US2 leak-probe).
- [ ] Evaluation harness uses **signal-level** assertions only —
      `SubtaskPayload` / `SubagentResult` pydantic validation outcomes, AST
      lint pass/fail, UUID grep count on `subagent_inputs.jsonl`. No string
      matching on model prose.
- [ ] Anti-pattern tests fail closed if history inheritance is reintroduced:
      (a) AST lint `test_no_history_leak.py` fails on any reference to
      `Coordinator._history` / `_messages` / `_transcript` / `_scratchpad`
      from `subagent.py`; (b) leak-probe integration test fails if the
      seeded UUID appears in any `subagent_inputs.jsonl` line.
- [ ] Assertion-integrity hashes in `.specify/context.json` match the locked
      test set — enforced at `/iikit-04-testify`.
- [ ] Per-kata `README.md` (written during `/iikit-07-implement`) covers
      objective, walkthrough, anti-pattern defense (leak-probe + AST lint +
      schema `extra=forbid`), run instructions, and reflection (per
      Principle VIII).
- [ ] Every non-trivial function (coordinator spawn path, payload builder,
      subagent run, result validation gate) carries a *why* comment tied
      to Principle IV or to the leak-probe anti-pattern (per Principle VIII).
- [ ] Short reflection note recorded in the README reflection section:
      observed failure mode the kata was designed to prevent (telepathy /
      inherited coordinator memory degrading attention and leaking policy).

## Reflection prompts (answered at implement time)

- Which field was most tempting to dump the coordinator's full history into
  (likely `instruction` or a free-form `context` field), and what stopped
  you from doing so?
- Where in the code would a future maintainer be tempted to "helpfully"
  forward `self._history` into a subagent, and which gate catches it first —
  the pydantic `extra="forbid"`, the AST lint, or the leak-probe UUID scan?
