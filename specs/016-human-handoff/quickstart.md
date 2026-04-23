# Kata 16 — Quickstart

## What you'll build

An `escalate_to_human` tool bound to a pydantic `HandoffPayload` schema. When
the agent invokes it, the session enters a hard-fail `SessionSuspended` state
(subsequent `messages.create` calls raise). Every payload is persisted to
`runs/handoffs/<escalation_id>.json` plus an index line in `index.jsonl`.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/016_human_handoff -v
```

Scenarios:
- policy-breach-mid-tool-call → escalation fires, session suspends.
- unknown-customer → `customer_id="unknown"` accepted as explicit sentinel.
- empty-actions-taken → permitted but logged.
- schema-missing-`severity` → rejected (SC-001 evolution gate).
- prose-only-handoff attempt using a decoy free-text tool → rejected (SC-002).
- session-suspended assertion: a second `messages.create` call after handoff
  raises `SessionSuspended`; 0 bytes of extra conversational text observed.

## Run against live API

```bash
LIVE_API=1 python -m katas.016_human_handoff.demo \
  --scenario policy-breach
```

Inspect: `runs/handoffs/<escalation_id>.json` + `runs/handoffs/index.jsonl`.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Valid escalation suspends session | US1, FR-001 | `policy_breach/` |
| Prose-only handoff rejected | US2, SC-002 | `prose_decoy_tool/` |
| Adding `severity` as required breaks legacy payload | US3, SC-001 | `legacy_payload_v10/` |
| Mid-tool-call escalation | Edge #1 | `mid_call/` |
| Repeated escalations in one session | Edge #4 | `double_escalation/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Raw-transcript anti-pattern defended by schema-bound tool.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- What's the smallest handoff payload that still lets a human act without
  paging the transcript? Did `issue_summary` hit that bar?
- If you bumped `severity` to required in v1.1, how would you roll out the
  migration in a real service?
