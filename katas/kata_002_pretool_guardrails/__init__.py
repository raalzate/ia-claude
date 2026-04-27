"""Kata 2 — Deterministic Guardrails via PreToolUse Hooks.

Anti-pattern this kata structurally defends against:
    *Prompt-only enforcement* of business policy. Asking the model "do not
    refund more than $500" eventually fails because (a) the model paraphrases
    the rule, (b) attention dilution drops the rule mid-context, and (c) the
    rule lives in free text rather than executable code. This kata moves the
    refund threshold OUT of the prompt and INTO a deterministic
    ``PreToolUseHook`` that runs before the SDK dispatches ``process_refund``,
    making the rule physically unbypassable (FR-008, Constitution Principle I).

Constitution principles enforced here:
    * I — Determinism Over Probability (NN): hook branches on pydantic
      validation + Decimal comparison, never on regex over prose.
    * II — Schema-Enforced Boundaries (NN): every boundary object is a
      pydantic v2 model with ``extra="forbid"`` and an explicit JSON Schema
      mirror under ``specs/002-pretool-guardrails/contracts/``.
    * VI — Human-in-the-Loop Escalation (NN): every ``policy_breach`` and
      ``hook_failure`` reject emits a typed ``EscalationEvent`` with
      ``actions_taken=[]`` (no action was taken, by construction).
    * VII — Provenance & Self-Audit: one JSONL line per invocation, verdict,
      escalation, and refund-API call lands under ``runs/<session>/``.
    * VIII — Mandatory Documentation (NN): the kata's narrative and the
      Claude-architecture-certification concepts it exercises live in
      ``notebook.ipynb`` adjacent to this package.
"""

__all__: list[str] = []
