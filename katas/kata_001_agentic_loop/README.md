# Kata 1 — Agentic Loop & Deterministic Control

> Build an agent loop that branches on `stop_reason` — and never on prose.

## Objective (in my own words)

Most "agent loops" you read in tutorials terminate because the model said
"I'm done" or "task complete". That works in the demo and silently fails
the first time the model phrases it differently. This kata builds the
opposite: a loop whose **only** signal for termination, dispatch, and
escalation is the structured `stop_reason` field returned by the
Anthropic Messages API. Every decision is observable, reproducible, and
auditable from a JSONL event log alone — no prose required.

This is the workshop's **non-negotiable** instantiation of Constitution
Principle I (Determinism Over Probability).

## Architecture walkthrough

```
┌────────────────────────────┐
│ Practitioner CLI (runner)  │
└──────────────┬─────────────┘
               │
┌──────────────┴─────────────┐      ┌──────────────────────┐
│       Agentic Loop         │ ───▶ │     Tool Registry    │
│   (loop.run / branch)      │      └──────────────────────┘
└──────────────┬─────────────┘
               │ emit(EventRecord)
┌──────────────┴─────────────┐      ┌──────────────────────┐
│ Event Log (JSONL, append)  │ ◀─── │ RecordedClient       │ (offline tests)
└────────────────────────────┘      │ LiveClient           │ (real API)
                                    └──────────────────────┘
```

| Module | Role |
|--------|------|
| `loop.py` | Single decision point. Branches on `stop_signal` only. AST-lint-protected against re-introduction of prose matching. |
| `client.py` | Thin injectable wrapper around the SDK. `RecordedClient` plays back fixtures; `LiveClient` calls the real API. |
| `tools.py` | `ToolRegistry` validates calls against declared JSON schemas (Principle II). Dispatcher converts raised exceptions to structured `ToolResult(error)` so the loop can continue (FR-007). Unknown tools / bad inputs raise `MalformedToolUse` for FR-008 halt. |
| `events.py` | Append-only JSONL writer. `extra="forbid"` on `EventRecord` makes it structurally impossible to slip a prose-derived field. Frozen-clock seam keeps SC-007 byte-identical. |
| `models.py` | Pydantic v2 entities crossing every module boundary. `Turn.assistant_text_blocks` is captured for the audit log only — `loop.py` is forbidden from reading it. |
| `session.py` | `RuntimeSession` owns the live state (history, registry, log). Keeps `loop.run` a pure function over its inputs. |
| `replay.py` | `reconstruct_trajectory(events.jsonl) → TrajectorySummary`. Proves SC-008 — the log alone is sufficient. |
| `runner.py` | CLI: `python -m katas.kata_001_agentic_loop.runner --prompt ... --fixture happy_path` (or `LIVE_API=1`). |

## Anti-pattern defense — how prose matching is structurally impossible

Three independent guards make a regression to prose matching catch fire:

1. **Source-level AST lint** (`tests/katas/kata_001_agentic_loop/lint/test_no_prose_matching.py`). It parses `loop.py` and fails the build on any of these:
   - `import re` / `from re import …`
   - `.find(…)`, `.index(…)`, `.search(…)`, `.match(…)`, `.startswith(…)`, `.endswith(…)`
   - `"literal" in some_var` and `some_var in "literal"`
   - **Reading** `Turn.assistant_text_blocks` (only writing it during `build_turn` is OK)
2. **Schema-level guard** (`models.py::EventRecord`). `extra="forbid"` rejects any prose-derived column on the audit log; the writer cannot persist a phrase even by accident.
3. **Behavioural guard** (`unit/test_decoy_phrases.py`). Drives every phrase from SC-004 through the loop with a non-terminal signal and asserts it does NOT halt.

Together: the loop cannot match on prose; the log cannot encode prose decisions; and tests will fail closed if either invariant is broken.

## Run instructions

```bash
# Install dev extras (one-time)
pip install -e ".[dev]"

# Run the kata against recorded fixtures (no API key needed)
pytest tests/katas/kata_001_agentic_loop -v

# Or run the CLI against a fixture
python -m katas.kata_001_agentic_loop.runner \
  --prompt "What's the weather in Bogotá?" \
  --fixture happy_path

# Live mode (needs ANTHROPIC_API_KEY)
LIVE_API=1 python -m katas.kata_001_agentic_loop.runner \
  --model claude-opus-4-7 \
  --prompt "What's the weather in Bogotá? Use the get_weather tool."
```

Artifacts produced under `runs/<session-id>/`:
- `events.jsonl` — append-only audit log (one line per loop iteration)

## Reproducibility (SC-007 / SC-008)

Two runs against the same fixture produce **byte-identical**
`(stop_signal, branch_taken)` columns. Mechanism:

- `events.serialize_record` uses `json.dumps(..., sort_keys=True, ensure_ascii=True)` — stable key ordering.
- `events.set_frozen_clock(when)` pins the timestamp during the SC-007 reproducibility tests so the only otherwise-floating column is locked.
- `replay.reconstruct_trajectory(path)` reads the JSONL and emits `(iterations, tool_invocations, termination_cause)` without consulting the model text or in-memory state — proving SC-008.

To verify locally:

```bash
# Two runs, diff the column slice we care about
LIVE_API=0 python -m katas.kata_001_agentic_loop.runner \
  --prompt "x" --fixture happy_path --runs-root /tmp/run_a
LIVE_API=0 python -m katas.kata_001_agentic_loop.runner \
  --prompt "x" --fixture happy_path --runs-root /tmp/run_b
jq -c '{s: .stop_signal, b: .branch_taken}' /tmp/run_a/*/events.jsonl > /tmp/a.cols
jq -c '{s: .stop_signal, b: .branch_taken}' /tmp/run_b/*/events.jsonl > /tmp/b.cols
diff /tmp/a.cols /tmp/b.cols   # expect: empty diff
```

## Reflection (Principle VIII)

**Which prose phrase was most tempting to match on, and what stopped you?**
"task complete" — the SC-004 list calls it out explicitly, and it shows up
verbatim in `decoy_phrase.json`. What stopped me was Principle I plus
**three** independent guards (AST lint, `extra="forbid"`, decoy unit tests).
Picking *one* would have been a single regression away from failing —
layered defence is what actually makes the determinism survive maintenance.

**Where in the code would `re` sneak back in during maintenance, and how
does the AST lint catch it?**
The most plausible regression is someone adding "graceful handling for
short truncations" by checking `if "..." in last_text_block`. The AST
lint walks `loop.py` and explicitly fails on any `Compare` node whose
operator is `In` / `NotIn` and whose left or right operand is a string
literal — and on every banned text method (`.find / .search / .match /
.startswith / .endswith`). It also blocks `assistant_text_blocks` from
being read inside the loop — closing the easy alternative of looking at
the text without using a string operator. The lint runs as a normal
pytest test, so it gates CI.

## What's deliberately out of scope

- Retries / backoff (no business value for this kata; would obscure determinism).
- Concurrent tool dispatch (sequential dispatch is enough to demonstrate FR-007).
- Persistent multi-session state (replay from JSONL is sufficient).
- Live-mode VCR-style cassette layer (the recorded fixtures are simple enough that we hand-craft them).

## Acceptance status

- ✅ All 6 US1 BDD scenarios pass (`signal_driven_termination.feature`)
- ✅ All 5 US2 BDD scenarios pass (`antipattern_prose_defense.feature`)
- ✅ All 4 US3 BDD scenarios pass (`observable_event_log.feature`)
- ✅ AST lint, decoy unit, schema unit, trajectory unit, history-replay unit all green
- ✅ `loop.py` line coverage ≥ 90% (currently 97%)
