<!--
Kata README template — Constitution Principle VIII (Mandatory Documentation).
Copied into katas/<NNN_slug>/README.md during /iikit-07-implement.
Every kata MUST ship this README populated; stale docs block merge.

Replace placeholders [LIKE THIS] with concrete content. Sections are
non-negotiable; reorder forbidden so the dashboard renderer can consume
them deterministically.
-->

# Kata [NN] — [Kata Title]

> **Branch**: `[NNN-slug]`
> **Constitution principles touched**: [I, II, …]
> **Status**: [Draft | In progress | Done]

## 1. Objective (in your own words)

Restate the kata objective from `specs/[NNN-slug]/spec.md` in 2–4 sentences using
your own phrasing. Cite the deterministic behavior the kata teaches and the
anti-pattern it forbids. No marketing prose — name the failure mode in plain
language.

## 2. Walkthrough

Step-by-step narrative of the implementation decisions. For each non-obvious
choice, explain *why* it exists, not just *what* it does. Reference the
relevant `tasks.md` task IDs (`T###`) and acceptance scenario tags
(`@TS-XXX`) so a reader can jump to the binding artifact.

Recommended subsections:

- **Entry point**: how the practitioner invokes the kata (`python -m …` or
  pytest target).
- **Control flow**: which signals drive the decision graph (e.g. `stop_reason`,
  hook verdict, `usage_fraction`). Quote the structured field, not a phrase
  from prose.
- **Schemas in play**: list every pydantic model / JSON schema that crosses
  a boundary, with `extra="forbid"` confirmed.
- **Persistence**: what gets written under `runs/<session-id>/` and why each
  artifact is sufficient for offline replay.

## 3. Anti-Pattern Defense

Name the exact failure mode the kata prevents (regex over prose, silent
fabrication, mid-buried critical rules, …) and explain how the code
structurally prevents reintroduction. Cite the AST lint or schema gate that
fails closed when the anti-pattern is reintroduced — the test that turns red
when somebody tries to weaken the defense. Reference the `@TS-XXX` scenarios
that demonstrate the regression guard.

## 4. Run Instructions

### Acceptance suite (offline)

```bash
pytest tests/katas/kata_[NNN_slug] -v
```

### Live API smoke (optional)

```bash
LIVE_API=1 python -m katas.kata_[NNN_slug].runner --[args]
```

### Reproducibility check

Document the diff command that proves SC-007-style byte-identical reruns when
the kata declares a reproducibility outcome. Otherwise mark this subsection
"N/A".

### Output reading guide

Explain what a reviewer looks for in `runs/<session-id>/events.jsonl` (or
equivalent) to confirm the kata met its objective without re-running the
model. Cite the field names, not prose.

## 5. Reflection

Two-paragraph self-audit:

1. **Failure mode observed**: which red test surfaced first, what the model
   tried to do, and which signal-level assertion blocked it. Name the
   commit/branch that made the failure permanent (link by SHA when known).
2. **What you'd ship next**: the next deterministic guardrail this kata
   suggests. Connect it to a downstream kata's principle if applicable
   (Principle I → Kata 1, II → Kata 5, III → Kata 11/18, IV → Kata 4/20,
   VII → Kata 20).

---

<!-- Populate before merging the kata. Empty section blocks merge. -->
