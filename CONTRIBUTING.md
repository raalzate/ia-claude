# Contributing

This is a teaching workshop. Every change MUST satisfy the
[`CONSTITUTION.md`](./CONSTITUTION.md). The non-negotiable principles to
keep in mind: Determinism Over Probability (I), Schema-Enforced Boundaries
(II), Test-First Kata Delivery (V), and Mandatory Documentation (VIII).

## One-time setup (after cloning)

```bash
bash scripts/install-hooks.sh
pip install -e ".[dev]"   # ruff, interrogate, pytest, pytest-bdd, pydantic, anthropic
```

The first command installs the IIKit assertion-integrity pre-commit hook
into `.git/hooks/pre-commit`. **Do not skip it.** The same check runs
server-side in CI (`assertion-integrity` workflow); a local commit that
bypasses the hook will fail CI.

If the hook ever blocks a commit with a hash mismatch, the fix is
**always** to re-run `/iikit-04-testify` for the touched feature — never
`git commit --no-verify`, never editing `.git/hooks/`, never plumbing
commands.

## Workflow per kata (FDD per Constitution §Development Workflow)

Stages 1–3 (overall model, feature list, plan-by-feature) are upfront and
already complete for the 20 katas. Per-kata work is sequential:

1. **Design by Feature** — `/iikit-04-testify` produces locked `.feature`
   files + assertion-integrity hashes. Tests fail red before any
   production code.
2. **Build by Feature** — `/iikit-05-tasks` then `/iikit-07-implement`
   write code task-by-task. Red → green → refactor.
3. **Document by Feature** — populate `katas/kata_NNN_<slug>/README.md`
   from `specs/_templates/kata-readme.md` (Principle VIII). Stale docs
   block merge.

Vertical delivery only: **never** start the next kata until the current
kata's docs ship.

## Required local checks before pushing

```bash
ruff check .
ruff format --check .
interrogate -c pyproject.toml katas/                # docstring coverage
pytest tests/                                        # full suite
bash .tessl/tiles/tessl-labs/intent-integrity-kit/skills/iikit-core/scripts/bash/verify-assertion-integrity.sh
```

CI mirrors these gates; passing locally is the cheapest way to avoid PR
churn. The assertion-integrity script enforces Principle V end-to-end.

## What never changes without explicit approval

- `CONSTITUTION.md` — amendments require a versioned PR per its
  `Governance` section.
- `.feature` files and `context.json` assertion hashes — re-run
  `/iikit-04-testify` instead of editing them by hand.
- `.git/hooks/pre-commit` — install via `scripts/install-hooks.sh`; do
  not edit.

## Filing changes

Each PR description MUST include the compliance line required by
`CONSTITUTION.md` `§Governance`:

> **Constitution compliance**: principles touched: [list]; all touched
> artifacts (`spec.md`, `plan.md`, `tasks.md`, `.feature`, README) remain
> consistent.

Code review is mandatory; the headless `architect-review` workflow runs
once Kata 13 lands and is the recommended automated reviewer. Human
review remains the final merge gate.
