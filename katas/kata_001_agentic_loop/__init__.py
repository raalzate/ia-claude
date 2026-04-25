"""Kata 1 — Agentic Loop & Deterministic Control.

This package implements an agent loop whose control flow branches **only** on
the structured `stop_reason` field of the Anthropic Messages API. Reading
response prose for control decisions is structurally forbidden (Constitution
Principle I — Determinism Over Probability, NON-NEGOTIABLE).
"""
