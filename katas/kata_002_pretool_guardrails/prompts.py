"""System-prompt string constants for the kata 2 agent.

Why this module is deliberately *empty of numbers*:
    Anti-pattern this kata defends against: prompt-only enforcement of the
    refund threshold. If the policy limit (``PolicyConfig.max_refund``) ever
    appears here as a numeric literal, the model becomes the enforcement
    surface — exactly the failure mode the kata exists to prevent (FR-008).

Machine check:
    ``tests/katas/kata_002_pretool_guardrails/lint/test_prompt_has_no_limit.py``
    parses this file with ``ast`` and fails the build if any string constant
    contains a numeric literal equal to the current
    ``PolicyConfig.max_refund``. Reviewer-enforced rules drift; AST checks do
    not.

What CAN live here:
    * Role descriptions ("You are a refunds support agent.")
    * Tool-use guidance ("Always call ``process_refund`` for refunds.")
    * Escalation language ("If the system rejects, summarize the structured
      error fields back to the user.")

What MUST NOT live here:
    * The number 500, 250, or any current/recent ``max_refund`` value.
    * Currency-tagged limits like "$500", "USD 500".
    * Any natural-language limit: "do not refund more than five hundred".
"""

from __future__ import annotations

SYSTEM_PROMPT_REFUNDS_AGENT: str = (
    "You are a refunds support agent. Always issue refunds by calling the "
    "process_refund tool with a structured payload containing tool_name, "
    "correlation_id, amount, currency, customer_id, and an optional reason. "
    "Never invent refund amounts; copy the amount the customer explicitly "
    "states. If the system returns a structured error, do not retry the same "
    "amount — summarize the rejection fields back to the customer and route "
    "them to the escalation_pathway given in the structured error."
)
"""Role + tool-use guidance only. Contains no numeric policy limit by design."""


PROMPT_CONSTANTS: tuple[str, ...] = (SYSTEM_PROMPT_REFUNDS_AGENT,)
"""All prompt strings exported from this module.

Why a single tuple: the AST lint walks ``ast.Constant`` nodes, but a runtime
helper (also exposed for tests that prefer iteration over reflection) needs
a flat collection of every prompt the agent sees. Keep this in sync if a new
prompt constant is added above.
"""
