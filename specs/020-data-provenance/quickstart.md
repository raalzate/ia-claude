# Kata 20 — Quickstart

## What you'll build

Subagents that extract `Claim` records with schema-required provenance
(`claim`, `source_name`, `source_url?`, `publication_date?`) from multiple
corporate manuals. A coordinator aggregates them, corroborates identical
claims, and — crucially — routes disagreements to a `ConflictSet +
ReviewTask` WITHOUT auto-picking a winner.

## Install

```bash
pip install -e ".[dev]"
```

## Run against fixtures

```bash
pytest tests/katas/020_data_provenance -v
```

Asserts:
- Every emitted `Claim` has `source_name` non-empty; `source_url` null only
  when explicitly internal.
- Seeded-contradictions corpus produces a `ConflictSet` with
  `conflict_detected=true`; no silent pick.
- Orphan claim (missing `source_name`) → pipeline fails closed
  (`OrphanClaimError`).
- Multi-source corroboration → `ClaimGroup.supporting_sources` lists all
  distinct sources.

## Aggregate a live corpus

```bash
LIVE_API=1 python -m katas.020_data_provenance.aggregate \
  --sources tests/katas/020_data_provenance/fixtures/manuals/ \
  --out runs/$(uuidgen)/aggregation-report.json
```

Inspect `conflicts[]` and `orphan_claims[]` — the latter MUST be empty on a
clean run.

## Scenario → spec mapping

| Scenario | Spec | Fixture |
|----------|------|---------|
| Every claim has provenance | US1, SC-001 | `consistent_manuals/` |
| Contradictions surface as ConflictSet | US2, SC-002 | `seeded_conflicts/` |
| Orphan claim rejected | US3, SC-004 | `orphan_claim/` |
| Internal-only source (no URL) accepted | Edge #4 | `internal_manual/` |
| Missing publication_date handled | Edge #1 | `no_date_manual/` |
| Duplicate claims across sources corroborate | Edge #3 | `corroborating_sources/` |

## "Done" checklist

- [x] `spec.md`, `plan.md`.
- [ ] `tasks.md`, `.feature` — pending.
- [x] Amalgamated-summary + silent-resolution anti-patterns defended by
      schema + aggregator contract.
- [ ] `README.md` — at `/iikit-07-implement`.

## Reflection

- When two sources gave slightly different numbers, what did the
  `numeric_divergence` audit reveal that you wouldn't have noticed otherwise?
- Which provenance field was most tempting to make optional — and what would
  it have cost you downstream?
