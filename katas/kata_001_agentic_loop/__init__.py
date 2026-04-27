"""Kata 1 — Agentic Loop & Deterministic Control.

Constitution Principle I (Determinism Over Probability): the loop branches
exclusively on the structured ``stop_reason`` signal returned by the Claude
Messages API; response prose is never inspected. This package is the source of
truth for that loop and ships an append-only JSONL event log so any run can be
reconstructed offline (Principle VII — Provenance & Self-Audit).
"""
