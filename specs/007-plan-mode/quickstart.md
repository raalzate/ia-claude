# Quickstart: Kata 7 — Safe Exploration via Plan Mode

Read this end-to-end before running anything. The kata's value is in the
signals (SessionMode transitions, plan_hash equality, scope-change halts),
not in model prose.

## 1. Install

From the repo root:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"   # installs anthropic, pydantic v2, pytest, pytest-bdd
```

Optional — only required if you want to hit the real Anthropic API:

```bash
export ANTHROPIC_API_KEY=sk-...
export LIVE_API=1          # default test run is fixture-only
```

## 2. Layout at a glance

```
katas/007_plan_mode/           # implementation (filled during /iikit-07-implement)
  session.py modes.py plan.py approval.py scope.py events.py
  client.py models.py runner.py README.md
specs/007-plan-mode/           # this feature's planning artifacts
  spec.md plan.md research.md data-model.md
  contracts/*.schema.json      # $id = kata-007
  checklists/requirements.md
specs/fixtures/refactor-plans/ # canonical target for written PlanDocuments
tests/katas/007_plan_mode/
  features/plan_mode.feature   # produced by /iikit-04-testify
  step_defs/ unit/ lint/ fixtures/
```

## 3. Run the fixture-based acceptance suite (default)

```bash
pytest tests/katas/007_plan_mode -q
```

This runs:

- `features/plan_mode.feature` via `pytest-bdd` against the 8 recorded
  fixtures under `tests/katas/007_plan_mode/fixtures/`.
- Unit tests for the mode gate, plan-hash integrity, scope-change
  detector, and plan-document serialization.
- Lint test asserting write-class tools are absent from `tools=[...]`
  whenever `SessionMode == "plan"` (structural SC-001 defense).

Expected: all green in under 10 seconds. No network calls.

## 4. Run the live-API smoke (opt-in)

```bash
LIVE_API=1 pytest tests/katas/007_plan_mode -q -k live
```

Hits the real SDK once per scenario. CI does **not** run these.

## 5. Run the kata end-to-end manually

```bash
python -m katas.007_plan_mode.runner \
    --request "Migrate auth from JWT to session cookies across 20 files"
```

Flow:

1. The runner starts in `SessionMode == "plan"`. The SDK is called with
   `tools=ReadOnlyTools` only. No write can occur.
2. The agent writes the plan to
   `specs/fixtures/refactor-plans/<task_id>.md` and halts.
3. Approve in a second process:

   ```bash
   python -m katas.007_plan_mode.runner approve \
       --task-id <task_id> --approved-by you@example.com
   ```

   This computes sha256 of the on-disk markdown, constructs a
   `HumanApprovalEvent`, writes it to
   `runs/<session-id>/approvals.jsonl`, and signals the waiting runner.

4. The runner verifies `event.plan_hash == compute_hash(current markdown)`.
   On match it transitions to `"execute"` and registers `WriteTools`. On
   mismatch it logs `reason="plan_hash_mismatch"` and stays in plan mode.

## 6. Scenario → spec mapping

| Fixture | User story | FR / SC covered | Entity under test |
|---|---|---|---|
| `normal_refactor.json` | US1 (P1) | FR-001, FR-003, FR-005, FR-006, SC-002, SC-003 | PlanDocument, SessionModeTransition |
| `write_attempt_in_plan_mode.json` | US2 (P2) | FR-002, FR-007, SC-001 | WriteAttemptedInPlanMode |
| `scope_creep_injection.json` | US3 (P3) | FR-004, SC-004 | ScopeChangeEvent |
| `plan_edit_after_approval.json` | Edge case (plan edited post-approval) | FR-001, D-003 | plan_hash mismatch path |
| `small_refactor.json` | Edge case (small task bypass) | FR-002 still holds | ScopeClassifier + mode gate |
| `infeasible_plan.json` | Edge case (infeasibility) | FR-001, FR-005 | SessionModeTransition(reason="infeasible_plan") |
| `interrupted_execution.json` | Edge case (interruption) | FR-005 | SessionModeTransition(reason="execution_interrupted") |
| `approval_revoked.json` | Edge case (revocation) | FR-001, FR-005 | HumanApprovalEvent(approval_note="revoked") |

## 7. Kata Completion Standards checklist

Mirrors Constitution §Kata Completion Standards (v1.3.0). A kata is DONE
only when every box is ticked.

- [ ] `spec.md`, `plan.md`, `tasks.md`, and `.feature` acceptance file
      exist for kata 7.
- [ ] Acceptance scenarios cover BOTH the stated objective (read-only
      planning then approved execution) AND the stated anti-pattern
      (jumping straight to edits on an unfamiliar codebase).
- [ ] Automated evaluation harness demonstrates the objective via
      signal-level assertions only:
      - SessionMode transition log completeness (SC-002),
      - plan_hash equality at transition (FR-001),
      - `tools=[...]` content inspection in plan mode (SC-001),
      - path-membership check pre-dispatch (SC-004),
      - schema conformance of every event (Principle II).
      No string-matching over model prose anywhere in the test suite.
- [ ] Anti-pattern tests (`write_attempt_in_plan_mode.json`,
      `scope_creep_injection.json`, `plan_edit_after_approval.json`) fail
      closed when the corresponding defense is reintroduced as a
      regression.
- [ ] Assertion-integrity hashes in `.specify/context.json` match the
      locked `.feature` set (regenerate via `/iikit-04-testify`, never
      hand-edit).
- [ ] `specs/007-plan-mode/README.md` exists covering: objective in own
      words, walkthrough of plan/execute gate decisions, anti-pattern
      defense, run instructions, reflection (Principle VIII).
- [ ] Every non-trivial function / hook / schema in `katas/007_plan_mode/`
      carries a *why* comment tied to the kata objective or anti-pattern
      (Principle VIII).
- [ ] Reflection note records the observed failure mode this kata is
      designed to prevent: advisory plan-mode without a structural
      write-gate, or scope creep past an approved file list. Lives in the
      README reflection section.
