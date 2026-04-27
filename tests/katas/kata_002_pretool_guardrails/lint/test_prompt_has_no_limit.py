"""TS-007 / FR-008: AST lint asserts ``prompts.py`` has no max_refund literal.

Why machine-enforced (not reviewer-enforced):
    The whole point of FR-008 is structural — a reviewer who misses a
    cleverly-phrased "five hundred" in a prompt re-introduces the
    prompt-only-enforcement anti-pattern silently. The AST lint walks every
    string literal in ``prompts.py`` and fails if any of them contains a
    numeric token equal to the active ``PolicyConfig.max_refund``.
"""

from __future__ import annotations

import ast
import json
import re
from decimal import Decimal
from pathlib import Path

from katas.kata_002_pretool_guardrails import prompts as prompts_module

PROMPT_FILE = Path(prompts_module.__file__)
# parents[4] = repo root (lint → kata → katas → tests → repo).
POLICY_FILE = Path(__file__).resolve().parents[4] / "config" / "policy.json"


def _string_constants(tree: ast.AST) -> list[str]:
    """Return every ``str`` constant appearing in the AST."""
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    ]


def _max_refund_tokens() -> set[str]:
    """Return string forms a reviewer might smuggle into a prompt.

    Why several forms: ``500``, ``500.00``, ``"$500"``, ``USD 500`` all
    encode the same number. A regex on ``\\b500\\b`` would miss
    ``$500`` (no word boundary before $); listing tokens explicitly
    keeps the lint surface readable and adjustable as the policy changes.
    """
    raw = json.loads(POLICY_FILE.read_text(encoding="utf-8"))["max_refund"]
    base = Decimal(raw)
    integer = str(base.to_integral_value())
    plain = str(base)
    return {
        integer,
        plain,
        plain.rstrip("0").rstrip("."),
        f"${integer}",
        f"${plain}",
        f"USD {integer}",
        f"USD {plain}",
    }


def test_prompts_module_contains_no_max_refund_literal() -> None:
    """No string in ``prompts.py`` may contain the current ``max_refund``."""
    source = PROMPT_FILE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    constants = _string_constants(tree)
    forbidden_tokens = _max_refund_tokens()

    # Strip the module docstring's deliberate mentions of forbidden tokens
    # (the docstring documents the rule by example). Constants whose source
    # location is the module-level docstring are excluded by checking node
    # parents — but ast doesn't track parents, so we walk again and skip
    # ``Expr(Constant)`` at module level.
    docstring_constants: set[int] = set()
    for node in ast.iter_child_nodes(tree):
        if (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            docstring_constants.add(id(node.value))

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_constants
        ):
            for token in forbidden_tokens:
                # Word-ish boundary check: ``token`` must appear as a
                # standalone numeric token, not inside another word.
                pattern = rf"(?<![A-Za-z0-9.]){re.escape(token)}(?![A-Za-z0-9])"
                assert not re.search(pattern, node.value), (
                    f"FR-008 violation: prompt constant contains forbidden token "
                    f"{token!r} — move the limit out of the prompt and rely on "
                    f"PolicyConfig.max_refund instead.\nOffending value: {node.value!r}"
                )

    # Also assert the module exposes at least one prompt constant — an empty
    # ``prompts.py`` would trivially pass the lint above.
    assert any(constants), "prompts.py is empty — at least one prompt is required"
